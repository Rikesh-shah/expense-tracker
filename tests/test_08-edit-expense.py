"""
Tests for the "Edit Expense" feature (Step 08).

Covers:
  - Unit tests for get_expense_by_id() DB helper
  - Unit tests for update_expense() DB helper
  - GET /expenses/<id>/edit — auth guard, 200 with pre-filled form, 404 cases
  - POST /expenses/<id>/edit — auth guard, validation errors, success path, DB side-effects
"""

import pytest
from database.db import get_db, get_expense_by_id, update_expense, insert_expense

# ---------------------------------------------------------------------------
# Helpers (mirrors the pattern in test_add_expense.py)
# ---------------------------------------------------------------------------

CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


def _login(client, name="Alice", email="alice@example.com", password="pass123"):
    client.post("/register", data={"name": name, "email": email, "password": password})
    client.post("/login", data={"email": email, "password": password})


def _get_user_id(email="alice@example.com"):
    """Return the user id for *email* using a direct DB connection."""
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row["id"]


def _create_user_direct(name, email, password_hash="hashed"):
    """Insert a user row directly and return the new user_id."""
    conn = get_db()
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    conn.commit()
    user_id = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[
        "id"
    ]
    conn.close()
    return user_id


def _create_expense_direct(
    user_id, amount=50.0, category="Food", date="2026-05-01", description="Test expense"
):
    """Insert an expense row directly and return the new expense id."""
    conn = get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    conn.commit()
    expense_id = conn.execute(
        "SELECT id FROM expenses WHERE user_id = ? AND description = ?",
        (user_id, description),
    ).fetchone()["id"]
    conn.close()
    return expense_id


# ---------------------------------------------------------------------------
# Unit tests for get_expense_by_id()
# ---------------------------------------------------------------------------


class TestGetExpenseById:
    """Direct DB-layer tests — no HTTP client involved."""

    def test_get_expense_by_id_valid_id_correct_user_returns_row(self, app):
        with app.app_context():
            user_id = _create_user_direct("Bob", "bob@example.com")
            expense_id = _create_expense_direct(
                user_id, amount=75.0, description="Dinner"
            )

            row = get_expense_by_id(expense_id, user_id)

            assert (
                row is not None
            ), "Should return the expense row for a matching id and user_id"
            assert (
                row["id"] == expense_id
            ), "Returned row id should match the queried expense_id"
            assert (
                row["user_id"] == user_id
            ), "Returned row should belong to the correct user"
            assert (
                float(row["amount"]) == 75.0
            ), "Amount should match the inserted value"

    def test_get_expense_by_id_valid_id_wrong_user_returns_none(self, app):
        with app.app_context():
            owner_id = _create_user_direct("Carol", "carol@example.com")
            other_id = _create_user_direct("Dave", "dave@example.com")
            expense_id = _create_expense_direct(owner_id, description="Owner's expense")

            result = get_expense_by_id(expense_id, other_id)

            assert (
                result is None
            ), "Should return None when the user_id does not match the expense owner"

    def test_get_expense_by_id_nonexistent_id_returns_none(self, app):
        with app.app_context():
            user_id = _create_user_direct("Eve", "eve@example.com")

            result = get_expense_by_id(99999, user_id)

            assert result is None, "Should return None for a non-existent expense_id"


# ---------------------------------------------------------------------------
# Unit tests for update_expense()
# ---------------------------------------------------------------------------


class TestUpdateExpense:
    """Direct DB-layer tests for update_expense()."""

    def test_update_expense_correct_user_updates_row_in_db(self, app):
        with app.app_context():
            user_id = _create_user_direct("Frank", "frank@example.com")
            expense_id = _create_expense_direct(
                user_id,
                amount=30.0,
                category="Food",
                date="2026-05-10",
                description="Old desc",
            )

            update_expense(
                expense_id, user_id, 99.0, "Health", "2026-06-01", "Updated desc"
            )

            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE id = ?", (expense_id,)
            ).fetchone()
            conn.close()

            assert row is not None, "Expense row should still exist after update"
            assert float(row["amount"]) == 99.0, "Amount should be updated to 99.0"
            assert row["category"] == "Health", "Category should be updated"
            assert row["date"] == "2026-06-01", "Date should be updated"
            assert row["description"] == "Updated desc", "Description should be updated"

    def test_update_expense_wrong_user_leaves_row_unchanged(self, app):
        with app.app_context():
            owner_id = _create_user_direct("Grace", "grace@example.com")
            other_id = _create_user_direct("Hank", "hank@example.com")
            expense_id = _create_expense_direct(
                owner_id,
                amount=40.0,
                category="Bills",
                date="2026-05-15",
                description="Electricity",
            )

            # Attempt update with a different user_id — should be a no-op
            update_expense(
                expense_id, other_id, 999.0, "Other", "2026-01-01", "Tampered"
            )

            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE id = ?", (expense_id,)
            ).fetchone()
            conn.close()

            assert row is not None, "Original expense row should still exist"
            assert (
                float(row["amount"]) == 40.0
            ), "Amount should be unchanged after wrong-user update attempt"
            assert row["category"] == "Bills", "Category should be unchanged"
            assert (
                row["description"] == "Electricity"
            ), "Description should be unchanged"


# ---------------------------------------------------------------------------
# GET /expenses/<id>/edit
# ---------------------------------------------------------------------------


class TestGetEditExpense:

    def test_get_edit_expense_unauthenticated_redirects_to_login(self, client):
        response = client.get("/expenses/1/edit")
        assert response.status_code == 302, "Unauthenticated GET should redirect (302)"
        assert (
            "/login" in response.headers["Location"]
        ), "Redirect target should be /login"

    def test_get_edit_expense_authenticated_own_expense_returns_200(self, app, client):
        _login(client)
        with app.app_context():
            user_id = _get_user_id("alice@example.com")
            expense_id = _create_expense_direct(
                user_id,
                amount=55.0,
                category="Transport",
                date="2026-05-20",
                description="Taxi ride",
            )

        response = client.get(f"/expenses/{expense_id}/edit")
        assert (
            response.status_code == 200
        ), "Authenticated GET for own expense should return 200"

    def test_get_edit_expense_form_contains_pre_filled_amount(self, app, client):
        _login(client)
        with app.app_context():
            user_id = _get_user_id("alice@example.com")
            expense_id = _create_expense_direct(
                user_id,
                amount=123.45,
                category="Food",
                date="2026-05-21",
                description="Restaurant",
            )

        body = client.get(f"/expenses/{expense_id}/edit").data.decode()
        assert "123.45" in body, "Form should be pre-filled with the expense amount"

    def test_get_edit_expense_form_contains_pre_filled_date(self, app, client):
        _login(client)
        with app.app_context():
            user_id = _get_user_id("alice@example.com")
            expense_id = _create_expense_direct(
                user_id,
                amount=20.0,
                category="Food",
                date="2026-05-22",
                description="Snack",
            )

        body = client.get(f"/expenses/{expense_id}/edit").data.decode()
        assert "2026-05-22" in body, "Form should be pre-filled with the expense date"

    def test_get_edit_expense_form_contains_pre_filled_description(self, app, client):
        _login(client)
        with app.app_context():
            user_id = _get_user_id("alice@example.com")
            expense_id = _create_expense_direct(
                user_id,
                amount=20.0,
                category="Food",
                date="2026-05-23",
                description="PreFilledDesc",
            )

        body = client.get(f"/expenses/{expense_id}/edit").data.decode()
        assert (
            "PreFilledDesc" in body
        ), "Form should be pre-filled with the expense description"

    def test_get_edit_expense_form_has_correct_category_preselected(self, app, client):
        _login(client)
        with app.app_context():
            user_id = _get_user_id("alice@example.com")
            expense_id = _create_expense_direct(
                user_id,
                amount=30.0,
                category="Health",
                date="2026-05-24",
                description="Doctor",
            )

        body = client.get(f"/expenses/{expense_id}/edit").data.decode()
        assert (
            "<select" in body
        ), "Response should include a <select> element for categories"
        # The selected category option should appear in the response.
        # Commonly this is rendered as `selected` next to the matching option value.
        assert (
            "Health" in body
        ), "Response body should contain the current category 'Health'"

    def test_get_edit_expense_form_contains_all_seven_categories(self, app, client):
        _login(client)
        with app.app_context():
            user_id = _get_user_id("alice@example.com")
            expense_id = _create_expense_direct(user_id)

        body = client.get(f"/expenses/{expense_id}/edit").data.decode()
        for category in CATEGORIES:
            assert (
                category in body
            ), f"Category '{category}' should appear in the edit form"

    def test_get_edit_expense_other_users_expense_returns_404(self, app, client):
        _login(client)
        with app.app_context():
            other_id = _create_user_direct("Other", "other@example.com")
            expense_id = _create_expense_direct(
                other_id, amount=10.0, description="Not mine"
            )

        response = client.get(f"/expenses/{expense_id}/edit")
        assert (
            response.status_code == 404
        ), "Accessing another user's expense via GET should return 404"

    def test_get_edit_expense_nonexistent_id_returns_404(self, client):
        _login(client)
        response = client.get("/expenses/99999/edit")
        assert (
            response.status_code == 404
        ), "GET for non-existent expense id should return 404"


# ---------------------------------------------------------------------------
# POST /expenses/<id>/edit — auth guard
# ---------------------------------------------------------------------------


class TestPostEditExpenseAuthGuard:

    def test_post_edit_expense_unauthenticated_redirects_to_login(self, client):
        response = client.post(
            "/expenses/1/edit",
            data={
                "amount": "50.0",
                "category": "Food",
                "date": "2026-03-20",
                "description": "Lunch",
            },
        )
        assert response.status_code == 302, "Unauthenticated POST should redirect (302)"
        assert (
            "/login" in response.headers["Location"]
        ), "Redirect target should be /login"


# ---------------------------------------------------------------------------
# POST /expenses/<id>/edit — 404 ownership guard
# ---------------------------------------------------------------------------


class TestPostEditExpenseOwnershipGuard:

    def test_post_edit_expense_other_users_expense_returns_404(self, app, client):
        _login(client)
        with app.app_context():
            other_id = _create_user_direct("Zara", "zara@example.com")
            expense_id = _create_expense_direct(
                other_id, amount=80.0, description="Zara's expense"
            )

        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "80.0",
                "category": "Food",
                "date": "2026-03-20",
                "description": "Tampered",
            },
        )
        assert (
            response.status_code == 404
        ), "POSTing to another user's expense should return 404"


# ---------------------------------------------------------------------------
# POST /expenses/<id>/edit — validation errors
# ---------------------------------------------------------------------------


class TestPostEditExpenseValidation:

    def _create_own_expense(self, app, client):
        """Helper to insert and return an expense id owned by alice (already logged in)."""
        with app.app_context():
            user_id = _get_user_id("alice@example.com")
            return _create_expense_direct(
                user_id,
                amount=60.0,
                category="Food",
                date="2026-05-30",
                description="Original",
            )

    def test_post_missing_amount_returns_200_with_error(self, app, client):
        _login(client)
        expense_id = self._create_own_expense(app, client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "category": "Food",
                "date": "2026-03-20",
                "description": "Lunch",
            },
        )
        assert (
            response.status_code == 200
        ), "Missing amount should re-render the form (200)"
        body = response.data.decode()
        assert "<form" in body, "Form should be re-rendered on validation error"

    def test_post_amount_zero_returns_200_with_error(self, app, client):
        _login(client)
        expense_id = self._create_own_expense(app, client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "0",
                "category": "Food",
                "date": "2026-03-20",
                "description": "Lunch",
            },
        )
        assert response.status_code == 200, "Amount=0 should re-render the form (200)"
        body = response.data.decode()
        assert "<form" in body, "Form should be re-rendered on validation error"

    def test_post_non_numeric_amount_returns_200_with_error(self, app, client):
        _login(client)
        expense_id = self._create_own_expense(app, client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "abc",
                "category": "Food",
                "date": "2026-03-20",
                "description": "Lunch",
            },
        )
        assert (
            response.status_code == 200
        ), "Non-numeric amount should re-render the form (200)"
        body = response.data.decode()
        assert "<form" in body, "Form should be re-rendered on validation error"

    def test_post_invalid_category_returns_200_with_error(self, app, client):
        _login(client)
        expense_id = self._create_own_expense(app, client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "50.0",
                "category": "NotACategory",
                "date": "2026-03-20",
                "description": "Lunch",
            },
        )
        assert (
            response.status_code == 200
        ), "Invalid category should re-render the form (200)"
        body = response.data.decode()
        assert "<form" in body, "Form should be re-rendered on validation error"

    def test_post_invalid_date_string_returns_200_with_error(self, app, client):
        _login(client)
        expense_id = self._create_own_expense(app, client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "50.0",
                "category": "Food",
                "date": "not-a-date",
                "description": "Lunch",
            },
        )
        assert (
            response.status_code == 200
        ), "Invalid date should re-render the form (200)"
        body = response.data.decode()
        assert "<form" in body, "Form should be re-rendered on validation error"

    def test_post_validation_error_response_contains_error_message(self, app, client):
        _login(client)
        expense_id = self._create_own_expense(app, client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "0",
                "category": "Food",
                "date": "2026-03-20",
                "description": "Lunch",
            },
        )
        body = response.data.decode()
        assert len(body) > 0, "Response body should not be empty"
        # The form is re-rendered — confirm it still has the category select
        assert (
            "<select" in body
        ), "Category select should be present in the re-rendered form"


# ---------------------------------------------------------------------------
# POST /expenses/<id>/edit — success path
# ---------------------------------------------------------------------------


class TestPostEditExpenseSuccess:

    def test_post_valid_data_redirects_to_profile(self, app, client):
        _login(client)
        with app.app_context():
            user_id = _get_user_id("alice@example.com")
            expense_id = _create_expense_direct(
                user_id,
                amount=50.0,
                category="Food",
                date="2026-05-01",
                description="Before edit",
            )

        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "75.0",
                "category": "Health",
                "date": "2026-06-15",
                "description": "After edit",
            },
        )
        assert response.status_code == 302, "Valid POST should redirect (302)"
        assert "/profile" in response.headers["Location"], "Should redirect to /profile"

    def test_post_valid_data_updates_row_in_db(self, app, client):
        _login(client)
        with app.app_context():
            user_id = _get_user_id("alice@example.com")
            expense_id = _create_expense_direct(
                user_id,
                amount=50.0,
                category="Food",
                date="2026-05-01",
                description="Original value",
            )

        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "88.0",
                "category": "Bills",
                "date": "2026-07-04",
                "description": "Updated value",
            },
        )

        with app.app_context():
            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE id = ?", (expense_id,)
            ).fetchone()
            conn.close()

        assert row is not None, "Expense row should still exist after update"
        assert float(row["amount"]) == 88.0, "Amount should reflect the updated value"
        assert row["category"] == "Bills", "Category should reflect the updated value"
        assert row["date"] == "2026-07-04", "Date should reflect the updated value"
        assert (
            row["description"] == "Updated value"
        ), "Description should reflect the updated value"

    def test_post_no_description_redirects_to_profile(self, app, client):
        _login(client)
        with app.app_context():
            user_id = _get_user_id("alice@example.com")
            expense_id = _create_expense_direct(
                user_id,
                amount=20.0,
                category="Transport",
                date="2026-05-10",
                description="Has description",
            )

        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "20.0",
                "category": "Transport",
                "date": "2026-05-10",
                "description": "",
            },
        )
        assert (
            response.status_code == 302
        ), "POST without description should redirect (302)"
        assert "/profile" in response.headers["Location"], "Should redirect to /profile"

    def test_post_no_description_stores_null_in_db(self, app, client):
        _login(client)
        with app.app_context():
            user_id = _get_user_id("alice@example.com")
            expense_id = _create_expense_direct(
                user_id,
                amount=20.0,
                category="Transport",
                date="2026-05-11",
                description="Will be cleared",
            )

        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "20.0",
                "category": "Transport",
                "date": "2026-05-11",
                "description": "",
            },
        )

        with app.app_context():
            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE id = ?", (expense_id,)
            ).fetchone()
            conn.close()

        assert row is not None, "Expense row should still exist after update"
        assert (
            row["description"] is None or row["description"] == ""
        ), "Description should be NULL or empty when submitted blank"

    def test_post_valid_data_does_not_change_user_id(self, app, client):
        _login(client)
        with app.app_context():
            user_id = _get_user_id("alice@example.com")
            expense_id = _create_expense_direct(
                user_id,
                amount=50.0,
                category="Food",
                date="2026-05-20",
                description="Check ownership",
            )

        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "50.0",
                "category": "Food",
                "date": "2026-05-20",
                "description": "Still alice",
            },
        )

        with app.app_context():
            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE id = ?", (expense_id,)
            ).fetchone()
            expected_user_id = _get_user_id("alice@example.com")
            conn.close()

        assert (
            row["user_id"] == expected_user_id
        ), "user_id on the expense should not change after edit"


# ---------------------------------------------------------------------------
# POST /expenses/<id>/edit — parametrized validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "amount,category,date,description",
    [
        ("", "Food", "2026-03-20", "Lunch"),  # empty amount
        ("0", "Food", "2026-03-20", "Lunch"),  # zero
        ("-5", "Food", "2026-03-20", "Lunch"),  # negative
        ("abc", "Food", "2026-03-20", "Lunch"),  # non-numeric
        ("50", "InvalidCategory", "2026-03-20", "Lunch"),  # bad category
        ("50", "Food", "20-03-2026", "Lunch"),  # wrong date format
        ("50", "Food", "not-a-date", "Lunch"),  # garbage date
    ],
)
def test_post_invalid_inputs_return_200(
    app, client, amount, category, date, description
):
    """Any invalid combination should re-render the form (200), never redirect."""
    _login(client)
    with app.app_context():
        user_id = _get_user_id("alice@example.com")
        expense_id = _create_expense_direct(
            user_id,
            amount=50.0,
            category="Food",
            date="2026-03-20",
            description="Parametrize target",
        )

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={
            "amount": amount,
            "category": category,
            "date": date,
            "description": description,
        },
    )
    assert response.status_code == 200, (
        f"Expected 200 for invalid input (amount={amount!r}, category={category!r}, "
        f"date={date!r}) but got {response.status_code}"
    )
