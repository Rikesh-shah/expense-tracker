"""
Tests for the "Delete Expense" feature (Step 09).

Covers:
  - Unit tests for delete_expense() DB helper
  - POST /expenses/<id>/delete — auth guard, 404s, success path, method guard
"""

import pytest
from database.db import get_db, delete_expense

# ---------------------------------------------------------------------------
# Helpers (mirrors test_edit_expense.py conventions)
# ---------------------------------------------------------------------------


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


def _row_exists(expense_id):
    """Return True if an expense row with this id still exists in the DB."""
    conn = get_db()
    row = conn.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    return row is not None


# ---------------------------------------------------------------------------
# Unit tests for delete_expense()
# ---------------------------------------------------------------------------


class TestDeleteExpenseDb:

    def test_returns_true_and_deletes_row_for_correct_owner(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client, description="To be deleted")
            user_id = _get_user_id()
            result = delete_expense(expense_id, user_id)
            still_exists = _row_exists(expense_id)
        assert (
            result is True
        ), "delete_expense should return True when the row is deleted"
        assert (
            not still_exists
        ), "Row should be gone from DB after delete with correct owner"

    def test_returns_false_and_leaves_row_for_wrong_owner(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client, description="Should survive wrong owner")
            result = delete_expense(expense_id, user_id=99999)
            still_exists = _row_exists(expense_id)
        assert (
            result is False
        ), "delete_expense should return False when user_id does not match"
        assert still_exists, "Row should remain in DB when user_id does not match"

    def test_returns_false_for_nonexistent_expense_id(self, app):
        with app.app_context():
            result = delete_expense(expense_id=99999, user_id=1)
        assert (
            result is False
        ), "delete_expense should return False for a non-existent expense_id"


# ---------------------------------------------------------------------------
# Route tests — POST /expenses/<id>/delete
# ---------------------------------------------------------------------------


class TestDeleteExpenseRoute:

    def test_unauthenticated_post_redirects_to_login(self, client):
        response = client.post("/expenses/1/delete")
        assert response.status_code == 302, "Unauthenticated POST should redirect"
        assert (
            "/login" in response.headers["Location"]
        ), "Unauthenticated POST should redirect to /login"

    def test_authenticated_post_own_expense_redirects_to_profile(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client, description="Redirect test")
        response = client.post(f"/expenses/{expense_id}/delete")
        assert response.status_code == 302, "Successful delete should redirect"
        assert (
            "/profile" in response.headers["Location"]
        ), "Successful delete should redirect to /profile"

    def test_authenticated_post_own_expense_removes_row_from_db(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client, description="DB removal check")
        client.post(f"/expenses/{expense_id}/delete")
        with app.app_context():
            still_exists = _row_exists(expense_id)
        assert (
            not still_exists
        ), "Expense row should be removed from DB after successful delete"

    def test_authenticated_post_own_expense_flashes_expense_deleted(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client, description="Flash message check")
        response = client.post(f"/expenses/{expense_id}/delete", follow_redirects=True)
        body = response.data.decode()
        assert (
            "Expense deleted" in body
        ), "Flash message 'Expense deleted' should appear in the response after a successful delete"

    def test_authenticated_post_other_users_expense_returns_404(self, app, client):
        _login(client, name="Alice", email="alice@example.com")
        with app.app_context():
            expense_id = _seed_expense(client, description="Alice private expense")

        # Log in as Bob — he should not be able to delete Alice's expense
        _login(client, name="Bob", email="bob@example.com")
        response = client.post(f"/expenses/{expense_id}/delete")
        assert (
            response.status_code == 404
        ), "POSTing to another user's expense should return 404"

    def test_authenticated_post_other_users_expense_leaves_row_intact(
        self, app, client
    ):
        _login(client, name="Alice", email="alice@example.com")
        with app.app_context():
            expense_id = _seed_expense(client, description="Alice row stays")

        _login(client, name="Bob", email="bob@example.com")
        client.post(f"/expenses/{expense_id}/delete")
        with app.app_context():
            still_exists = _row_exists(expense_id)
        assert (
            still_exists
        ), "Row should remain in DB when a different user attempts to delete it"

    def test_authenticated_post_nonexistent_id_returns_404(self, client):
        _login(client)
        response = client.post("/expenses/99999/delete")
        assert (
            response.status_code == 404
        ), "POSTing to a non-existent expense id should return 404"

    def test_get_method_returns_405(self, app, client):
        _login(client)
        with app.app_context():
            expense_id = _seed_expense(client, description="Method guard check")
        response = client.get(f"/expenses/{expense_id}/delete")
        assert (
            response.status_code == 405
        ), "GET on a POST-only delete route should return 405 Method Not Allowed"
