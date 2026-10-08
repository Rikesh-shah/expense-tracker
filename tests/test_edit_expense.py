"""
Tests for the "Edit Expense" feature (Step 08).

Covers:
  - Unit tests for get_expense_by_id() and update_expense() DB helpers
  - GET /expenses/<id>/edit — auth guard, 404s, pre-filled form
  - POST /expenses/<id>/edit — auth guard, 404s, validation errors, success path
"""

import pytest
from database.db import get_db, get_expense_by_id, update_expense

# ---------------------------------------------------------------------------
# Helpers
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
    conn = get_db()
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row["id"]


def _seed_expense(
    client, amount="25.00", category="Food", date="2026-10-01", description="Test lunch"
):
    """POST to /expenses/add and return the new expense's id."""
    client.post(
        "/expenses/add",
        data={
            "amount": amount,
            "category": category,
            "date": date,
            "description": description,
        },
    )
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM expenses WHERE description = ?", (description,)
    ).fetchone()
    conn.close()
    return row["id"]


# ---------------------------------------------------------------------------
# Unit tests for get_expense_by_id()
# ---------------------------------------------------------------------------


class TestGetExpenseById:

    def test_returns_row_for_correct_owner(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client)
            user_id = _get_user_id()
            row = get_expense_by_id(expense_id, user_id)
        assert row is not None, "Should return the row when id and user_id match"
        assert row["id"] == expense_id

    def test_returns_none_for_wrong_owner(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client)
            row = get_expense_by_id(expense_id, user_id=99999)
        assert row is None, "Should return None when user_id does not match"

    def test_returns_none_for_nonexistent_id(self, app):
        with app.app_context():
            row = get_expense_by_id(expense_id=99999, user_id=1)
        assert row is None, "Should return None when the expense id does not exist"


# ---------------------------------------------------------------------------
# Unit tests for update_expense()
# ---------------------------------------------------------------------------


class TestUpdateExpense:

    def test_updates_row_for_correct_owner(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client, amount="25.00", description="Original")
            user_id = _get_user_id()
            update_expense(
                expense_id, user_id, 99.0, "Bills", "2026-11-01", "Updated desc"
            )
            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE id = ?", (expense_id,)
            ).fetchone()
            conn.close()
        assert float(row["amount"]) == 99.0
        assert row["category"] == "Bills"
        assert row["date"] == "2026-11-01"
        assert row["description"] == "Updated desc"

    def test_does_not_update_row_for_wrong_owner(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client, amount="25.00", description="Unchanged")
            update_expense(
                expense_id,
                user_id=99999,
                amount=999.0,
                category="Shopping",
                date="2026-12-01",
                description="Hacked",
            )
            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE id = ?", (expense_id,)
            ).fetchone()
            conn.close()
        assert (
            float(row["amount"]) == 25.0
        ), "Row should be unchanged when user_id does not match"
        assert row["description"] == "Unchanged"


# ---------------------------------------------------------------------------
# GET /expenses/<id>/edit
# ---------------------------------------------------------------------------


class TestGetEditExpense:

    def test_unauthenticated_redirects_to_login(self, client):
        response = client.get("/expenses/1/edit")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_authenticated_own_expense_returns_200(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client)
        response = client.get(f"/expenses/{expense_id}/edit")
        assert response.status_code == 200

    def test_form_prefilled_with_existing_values(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(
                client,
                amount="42.00",
                category="Health",
                date="2026-10-05",
                description="Pharmacy visit",
            )
        body = client.get(f"/expenses/{expense_id}/edit").data.decode()
        assert "42.0" in body, "Amount should be pre-filled"
        assert "2026-10-05" in body, "Date should be pre-filled"
        assert "Pharmacy visit" in body, "Description should be pre-filled"

    def test_correct_category_preselected(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(
                client, category="Transport", description="Bus pass"
            )
        body = client.get(f"/expenses/{expense_id}/edit").data.decode()
        assert 'value="Transport"' in body and "selected" in body

    def test_nonexistent_id_returns_404(self, client):
        _login(client)
        response = client.get("/expenses/99999/edit")
        assert response.status_code == 404

    def test_other_users_expense_returns_404(self, app, client):
        _login(client, name="Alice", email="alice@example.com")
        with app.app_context():
            expense_id = _seed_expense(client, description="Alice expense")

        # Log in as a second user
        _login(client, name="Bob", email="bob@example.com")
        response = client.get(f"/expenses/{expense_id}/edit")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /expenses/<id>/edit — auth guard
# ---------------------------------------------------------------------------


class TestPostEditExpenseAuthGuard:

    def test_unauthenticated_redirects_to_login(self, client):
        response = client.post(
            "/expenses/1/edit",
            data={
                "amount": "50.0",
                "category": "Food",
                "date": "2026-10-01",
                "description": "Lunch",
            },
        )
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ---------------------------------------------------------------------------
# POST /expenses/<id>/edit — 404 guards
# ---------------------------------------------------------------------------


class TestPostEditExpense404:

    def test_nonexistent_id_returns_404(self, client):
        _login(client)
        response = client.post(
            "/expenses/99999/edit",
            data={
                "amount": "50.0",
                "category": "Food",
                "date": "2026-10-01",
                "description": "Lunch",
            },
        )
        assert response.status_code == 404

    def test_other_users_expense_returns_404(self, app, client):
        _login(client, name="Alice", email="alice@example.com")
        with app.app_context():
            expense_id = _seed_expense(client, description="Alice only")

        _login(client, name="Bob", email="bob@example.com")
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "50.0",
                "category": "Food",
                "date": "2026-10-01",
                "description": "Hijacked",
            },
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /expenses/<id>/edit — validation errors
# ---------------------------------------------------------------------------


class TestPostEditExpenseValidation:

    def test_missing_amount_returns_200_with_error(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "category": "Food",
                "date": "2026-10-01",
                "description": "Lunch",
            },
        )
        assert response.status_code == 200
        assert "<form" in response.data.decode()

    def test_amount_zero_returns_200_with_error(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "0",
                "category": "Food",
                "date": "2026-10-01",
                "description": "Lunch",
            },
        )
        assert response.status_code == 200
        assert "<form" in response.data.decode()

    def test_negative_amount_returns_200_with_error(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "-5",
                "category": "Food",
                "date": "2026-10-01",
                "description": "Lunch",
            },
        )
        assert response.status_code == 200

    def test_non_numeric_amount_returns_200_with_error(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "abc",
                "category": "Food",
                "date": "2026-10-01",
                "description": "Lunch",
            },
        )
        assert response.status_code == 200
        assert "<form" in response.data.decode()

    def test_invalid_category_returns_200_with_error(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "50.0",
                "category": "InvalidCategory",
                "date": "2026-10-01",
                "description": "Lunch",
            },
        )
        assert response.status_code == 200
        assert "<form" in response.data.decode()

    def test_invalid_date_returns_200_with_error(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "50.0",
                "category": "Food",
                "date": "not-a-date",
                "description": "Lunch",
            },
        )
        assert response.status_code == 200
        assert "<form" in response.data.decode()

    def test_validation_error_preserves_submitted_values(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "abc",
                "category": "Food",
                "date": "2026-10-01",
                "description": "My special note",
            },
        )
        body = response.data.decode()
        assert (
            "My special note" in body
        ), "Submitted values should be preserved on error"


# ---------------------------------------------------------------------------
# POST /expenses/<id>/edit — success path
# ---------------------------------------------------------------------------


class TestPostEditExpenseSuccess:

    def test_valid_data_redirects_to_profile(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "99.0",
                "category": "Bills",
                "date": "2026-11-01",
                "description": "Updated",
            },
        )
        assert response.status_code == 302
        assert "/profile" in response.headers["Location"]

    def test_valid_data_updates_db(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(
                client, amount="25.00", description="Before edit"
            )
        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "88.0",
                "category": "Shopping",
                "date": "2026-11-15",
                "description": "After edit",
            },
        )
        with app.app_context():
            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE id = ?", (expense_id,)
            ).fetchone()
            conn.close()
        assert float(row["amount"]) == 88.0
        assert row["category"] == "Shopping"
        assert row["date"] == "2026-11-15"
        assert row["description"] == "After edit"

    def test_empty_description_saves_as_null(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client, description="Had a description")
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "10.0",
                "category": "Other",
                "date": "2026-11-01",
                "description": "",
            },
        )
        assert response.status_code == 302
        with app.app_context():
            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE id = ?", (expense_id,)
            ).fetchone()
            conn.close()
        assert row["description"] is None or row["description"] == ""

    def test_success_flashes_expense_updated(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client)
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "50.0",
                "category": "Food",
                "date": "2026-11-01",
                "description": "Dinner",
            },
            follow_redirects=True,
        )
        body = response.data.decode()
        assert "Expense updated" in body


# ---------------------------------------------------------------------------
# Parametrized validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "amount,category,date,description",
    [
        ("", "Food", "2026-10-01", "Lunch"),
        ("0", "Food", "2026-10-01", "Lunch"),
        ("-5", "Food", "2026-10-01", "Lunch"),
        ("abc", "Food", "2026-10-01", "Lunch"),
        ("50", "InvalidCategory", "2026-10-01", "Lunch"),
        ("50", "Food", "01-10-2026", "Lunch"),
        ("50", "Food", "not-a-date", "Lunch"),
    ],
)
def test_post_invalid_inputs_return_200(
    app, client, amount, category, date, description
):
    """Any invalid combination should re-render the form (200), never redirect."""
    _login(client)
    with app.app_context():
        expense_id = _seed_expense(client)
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
