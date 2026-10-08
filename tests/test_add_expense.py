"""
Tests for the "Add Expense" feature (Step 07).

Covers:
  - Unit tests for insert_expense() DB helper
  - GET /expenses/add — auth guard and page rendering
  - POST /expenses/add — auth guard, validation errors, success path, DB side-effects
"""

import pytest
from database.db import get_db, insert_expense

# ---------------------------------------------------------------------------
# Helpers (mirrors the pattern in test_profile.py)
# ---------------------------------------------------------------------------

CATEGORIES = [
    "Food", "Transport", "Bills", "Health",
    "Entertainment", "Shopping", "Other",
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


# ---------------------------------------------------------------------------
# Unit tests for insert_expense()
# ---------------------------------------------------------------------------

class TestInsertExpense:
    """Direct DB-layer tests — no HTTP client involved."""

    def test_insert_expense_valid_inputs_returns_lastrowid(self, app):
        with app.app_context():
            # Create a bare user so we have a valid user_id.
            conn = get_db()
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Bob", "bob@example.com", "hashed"),
            )
            conn.commit()
            user_id = conn.execute(
                "SELECT id FROM users WHERE email = ?", ("bob@example.com",)
            ).fetchone()["id"]
            conn.close()

            row_id = insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")

            assert row_id is not None, "insert_expense should return a lastrowid"
            assert isinstance(row_id, int), "lastrowid should be an integer"
            assert row_id > 0, "lastrowid should be positive"

    def test_insert_expense_row_persisted_in_db(self, app):
        with app.app_context():
            conn = get_db()
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Carol", "carol@example.com", "hashed"),
            )
            conn.commit()
            user_id = conn.execute(
                "SELECT id FROM users WHERE email = ?", ("carol@example.com",)
            ).fetchone()["id"]
            conn.close()

            insert_expense(user_id, 50.0, "Food", "2026-03-20", "Lunch")

            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE user_id = ? AND description = ?",
                (user_id, "Lunch"),
            ).fetchone()
            conn.close()

            assert row is not None, "Expense row should exist in DB after insert"
            assert float(row["amount"]) == 50.0, "Amount should be persisted correctly"
            assert row["category"] == "Food", "Category should be persisted correctly"
            assert row["date"] == "2026-03-20", "Date should be persisted correctly"
            assert row["description"] == "Lunch", "Description should be persisted correctly"

    def test_insert_expense_null_description_persisted(self, app):
        with app.app_context():
            conn = get_db()
            conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Dave", "dave@example.com", "hashed"),
            )
            conn.commit()
            user_id = conn.execute(
                "SELECT id FROM users WHERE email = ?", ("dave@example.com",)
            ).fetchone()["id"]
            conn.close()

            row_id = insert_expense(user_id, 20.0, "Transport", "2026-04-01", None)

            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE id = ?", (row_id,)
            ).fetchone()
            conn.close()

            assert row is not None, "Expense row should exist even with NULL description"
            assert row["description"] is None, "Description should be NULL when None is passed"


# ---------------------------------------------------------------------------
# GET /expenses/add
# ---------------------------------------------------------------------------

class TestGetAddExpense:

    def test_get_add_expense_unauthenticated_redirects_to_login(self, client):
        response = client.get("/expenses/add")
        assert response.status_code == 302, "Unauthenticated GET should redirect"
        assert "/login" in response.headers["Location"], "Should redirect to /login"

    def test_get_add_expense_authenticated_returns_200(self, client):
        _login(client)
        response = client.get("/expenses/add")
        assert response.status_code == 200, "Authenticated GET should return 200"

    def test_get_add_expense_contains_form_with_post_method(self, client):
        _login(client)
        body = client.get("/expenses/add").data.decode()
        assert "<form" in body, "Response should contain a <form> element"
        assert "post" in body.lower(), "Form should use POST method"

    def test_get_add_expense_contains_select_element(self, client):
        _login(client)
        body = client.get("/expenses/add").data.decode()
        assert "<select" in body, "Response should contain a <select> element for categories"

    def test_get_add_expense_contains_all_seven_categories(self, client):
        _login(client)
        body = client.get("/expenses/add").data.decode()
        for category in CATEGORIES:
            assert category in body, f"Category '{category}' should appear in the form"

    def test_get_add_expense_contains_today_date(self, client):
        _login(client)
        body = client.get("/expenses/add").data.decode()
        # The route injects `today` — a date input should be present
        assert 'type="date"' in body or "date" in body, \
            "Response should include a date input field"


# ---------------------------------------------------------------------------
# POST /expenses/add — auth guard
# ---------------------------------------------------------------------------

class TestPostAddExpenseAuthGuard:

    def test_post_add_expense_unauthenticated_redirects_to_login(self, client):
        response = client.post("/expenses/add", data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert response.status_code == 302, "Unauthenticated POST should redirect"
        assert "/login" in response.headers["Location"], "Should redirect to /login"


# ---------------------------------------------------------------------------
# POST /expenses/add — validation errors
# ---------------------------------------------------------------------------

class TestPostAddExpenseValidation:

    def test_post_missing_amount_returns_200_with_error(self, client):
        _login(client)
        response = client.post("/expenses/add", data={
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert response.status_code == 200, "Missing amount should re-render the form (200)"
        body = response.data.decode()
        assert len(body) > 0, "Response body should not be empty"

    def test_post_amount_zero_returns_200_with_error(self, client):
        _login(client)
        response = client.post("/expenses/add", data={
            "amount": "0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert response.status_code == 200, "Amount=0 should re-render the form with an error"
        body = response.data.decode()
        # The form should still be present (re-render, not redirect)
        assert "<form" in body, "Form should be re-rendered on validation error"

    def test_post_negative_amount_returns_200_with_error(self, client):
        _login(client)
        response = client.post("/expenses/add", data={
            "amount": "-10",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Refund",
        })
        assert response.status_code == 200, "Negative amount should re-render the form"

    def test_post_non_numeric_amount_returns_200_with_error(self, client):
        _login(client)
        response = client.post("/expenses/add", data={
            "amount": "abc",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert response.status_code == 200, "Non-numeric amount should re-render the form"
        body = response.data.decode()
        assert "<form" in body, "Form should be re-rendered on validation error"

    def test_post_invalid_category_returns_200_with_error(self, client):
        _login(client)
        response = client.post("/expenses/add", data={
            "amount": "50.0",
            "category": "InvalidCategory",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert response.status_code == 200, "Invalid category should re-render the form"
        body = response.data.decode()
        assert "<form" in body, "Form should be re-rendered on validation error"

    def test_post_invalid_date_string_returns_200_with_error(self, client):
        _login(client)
        response = client.post("/expenses/add", data={
            "amount": "50.0",
            "category": "Food",
            "date": "not-a-date",
            "description": "Lunch",
        })
        assert response.status_code == 200, "Invalid date should re-render the form"
        body = response.data.decode()
        assert "<form" in body, "Form should be re-rendered on validation error"

    def test_post_validation_error_preserves_prior_form_values(self, client):
        _login(client)
        response = client.post("/expenses/add", data={
            "amount": "abc",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Fancy dinner",
        })
        body = response.data.decode()
        # The re-rendered form should echo back prior values so user doesn't retype everything
        assert "Fancy dinner" in body, "Prior description should be preserved on validation error"


# ---------------------------------------------------------------------------
# POST /expenses/add — success path
# ---------------------------------------------------------------------------

class TestPostAddExpenseSuccess:

    def test_post_valid_data_redirects_to_profile(self, client):
        _login(client)
        response = client.post("/expenses/add", data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        assert response.status_code == 302, "Valid POST should redirect"
        assert "/profile" in response.headers["Location"], "Should redirect to /profile"

    def test_post_valid_data_inserts_row_in_db(self, app, client):
        _login(client)
        client.post("/expenses/add", data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        })
        with app.app_context():
            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE description = ?", ("Lunch",)
            ).fetchone()
            conn.close()

        assert row is not None, "Expense row should exist in DB after successful POST"
        assert float(row["amount"]) == 50.0, "Amount should match submitted value"
        assert row["category"] == "Food", "Category should match submitted value"
        assert row["date"] == "2026-03-20", "Date should match submitted value"

    def test_post_no_description_redirects_to_profile(self, client):
        _login(client)
        response = client.post("/expenses/add", data={
            "amount": "25.0",
            "category": "Transport",
            "date": "2026-03-21",
            "description": "",
        })
        assert response.status_code == 302, "POST without description should redirect"
        assert "/profile" in response.headers["Location"], "Should redirect to /profile"

    def test_post_no_description_inserts_null_description_in_db(self, app, client):
        _login(client)
        client.post("/expenses/add", data={
            "amount": "25.0",
            "category": "Transport",
            "date": "2026-03-21",
            "description": "",
        })
        with app.app_context():
            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE category = ? AND date = ?",
                ("Transport", "2026-03-21"),
            ).fetchone()
            conn.close()

        assert row is not None, "Expense row should be inserted even without description"
        assert row["description"] is None or row["description"] == "", \
            "Description should be NULL or empty string when not provided"

    def test_post_valid_data_flashes_success_message(self, client):
        _login(client)
        response = client.post("/expenses/add", data={
            "amount": "75.0",
            "category": "Bills",
            "date": "2026-03-22",
            "description": "Electricity",
        }, follow_redirects=True)
        body = response.data.decode()
        assert "Expense added" in body, \
            "Flash message 'Expense added.' should appear on the profile page after success"

    def test_post_valid_data_expense_belongs_to_logged_in_user(self, app, client):
        _login(client)
        client.post("/expenses/add", data={
            "amount": "30.0",
            "category": "Health",
            "date": "2026-03-23",
            "description": "Vitamins",
        })
        with app.app_context():
            user_id = _get_user_id("alice@example.com")
            conn = get_db()
            row = conn.execute(
                "SELECT * FROM expenses WHERE description = ?", ("Vitamins",)
            ).fetchone()
            conn.close()

        assert row is not None, "Expense should exist in DB"
        assert row["user_id"] == user_id, \
            "Expense should be associated with the logged-in user's id"


# ---------------------------------------------------------------------------
# POST /expenses/add — parametrized validation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("amount,category,date,description", [
    ("",    "Food",            "2026-03-20", "Lunch"),       # empty amount
    ("0",   "Food",            "2026-03-20", "Lunch"),       # zero
    ("-5",  "Food",            "2026-03-20", "Lunch"),       # negative
    ("abc", "Food",            "2026-03-20", "Lunch"),       # non-numeric
    ("50",  "InvalidCategory", "2026-03-20", "Lunch"),       # bad category
    ("50",  "Food",            "20-03-2026", "Lunch"),       # wrong date format
    ("50",  "Food",            "not-a-date", "Lunch"),       # garbage date
])
def test_post_invalid_inputs_return_200(client, amount, category, date, description):
    """Any invalid combination should re-render the form (200), never redirect."""
    _login(client)
    response = client.post("/expenses/add", data={
        "amount": amount,
        "category": category,
        "date": date,
        "description": description,
    })
    assert response.status_code == 200, (
        f"Expected 200 for invalid input (amount={amount!r}, category={category!r}, "
        f"date={date!r}) but got {response.status_code}"
    )
