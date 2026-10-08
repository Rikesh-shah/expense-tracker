import re
import pytest
from database.db import get_db


def _login(client, name="Alice", email="alice@example.com", password="pass123"):
    client.post("/register", data={"name": name, "email": email, "password": password})
    client.post("/login",    data={"email": email, "password": password})


def _seed_expense(client, amount, category, date, description):
    conn = get_db()
    user_id = conn.execute(
        'SELECT id FROM users WHERE email = ?', ('alice@example.com',)
    ).fetchone()['id']
    conn.execute(
        'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
        (user_id, amount, category, date, description)
    )
    conn.commit()
    conn.close()


def test_profile_redirects_unauthenticated(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_returns_200_when_logged_in(client):
    _login(client)
    response = client.get("/profile")
    assert response.status_code == 200


def test_profile_shows_user_info(client):
    _login(client)
    body = client.get("/profile").data.decode()
    assert "Alice" in body
    assert "alice@example.com" in body
    assert re.search(r'\b20\d{2}\b', body), "member_since year not found in profile"


def test_profile_shows_stats(client):
    _login(client)
    _seed_expense(client, 100.00, "Food", "2026-10-01", "Lunch")
    _seed_expense(client, 50.00,  "Food", "2026-10-02", "Dinner")
    body = client.get("/profile").data.decode()
    assert "150.00" in body
    assert "2" in body
    assert "Food" in body


def test_profile_shows_transaction_table(client):
    _login(client)
    _seed_expense(client, 40.00, "Transport", "2026-10-01", "Bus pass")
    _seed_expense(client, 20.00, "Food",      "2026-10-02", "Coffee run")
    body = client.get("/profile").data.decode()
    assert "Bus pass" in body
    assert "Coffee run" in body


def test_profile_shows_category_breakdown(client):
    _login(client)
    _seed_expense(client, 100.00, "Shopping",  "2026-10-01", "Shoes")
    _seed_expense(client, 80.00,  "Utilities", "2026-10-02", "Electric")
    _seed_expense(client, 60.00,  "Transport", "2026-10-03", "Train")
    body = client.get("/profile").data.decode()
    assert "Shopping" in body
    assert "Utilities" in body
    assert "Transport" in body


def test_profile_has_no_hex_colours(client):
    _login(client)
    body = client.get("/profile").data.decode()
    hex_pattern = re.compile(r'#[0-9a-fA-F]{3,6}\b')
    assert not hex_pattern.search(body), "Hex colour found in rendered profile HTML"


# ---------------------------------------------------------------------------
# Date-range filter tests
# ---------------------------------------------------------------------------

_ALL_EXPENSES = [
    (42.50,  'Food',          '2026-10-01', 'Grocery run'),
    (28.00,  'Transport',     '2026-10-03', 'Monthly bus pass'),
    (120.00, 'Bills',         '2026-10-05', 'Electricity bill'),
    (35.00,  'Health',        '2026-10-07', 'Pharmacy'),
    (12.99,  'Entertainment', '2026-10-10', 'Streaming subscription'),
    (65.00,  'Shopping',      '2026-10-14', 'New clothing'),
    (8.50,   'Other',         '2026-10-18', 'Stationery'),
    (18.75,  'Food',          '2026-10-21', 'Restaurant lunch'),
]


def _seed_all_expenses(client):
    """Seed all eight spec expenses for the logged-in Alice account."""
    for amount, category, date, description in _ALL_EXPENSES:
        _seed_expense(client, amount, category, date, description)


def test_date_from_filter_excludes_earlier_transactions(client):
    """date_from=2026-10-05 — transactions before Oct 5 must not appear."""
    _login(client)
    _seed_all_expenses(client)
    body = client.get("/profile?date_from=2026-10-05").data.decode()
    assert "Grocery run" not in body, "Grocery run (Oct 1) should be excluded by date_from=2026-10-05"
    assert "Monthly bus pass" not in body, "Monthly bus pass (Oct 3) should be excluded by date_from=2026-10-05"
    assert "Electricity bill" in body, "Electricity bill (Oct 5) should appear — on the boundary"
    assert "Pharmacy" in body, "Pharmacy (Oct 7) should appear after date_from"
    assert "Streaming subscription" in body, "Streaming subscription (Oct 10) should appear after date_from"
    assert "New clothing" in body, "New clothing (Oct 14) should appear after date_from"
    assert "Stationery" in body, "Stationery (Oct 18) should appear after date_from"
    assert "Restaurant lunch" in body, "Restaurant lunch (Oct 21) should appear after date_from"


def test_date_to_filter_excludes_later_transactions(client):
    """date_to=2026-10-07 — transactions after Oct 7 must not appear."""
    _login(client)
    _seed_all_expenses(client)
    body = client.get("/profile?date_to=2026-10-07").data.decode()
    assert "Streaming subscription" not in body, "Streaming subscription (Oct 10) should be excluded by date_to=2026-10-07"
    assert "New clothing" not in body, "New clothing (Oct 14) should be excluded"
    assert "Stationery" not in body, "Stationery (Oct 18) should be excluded"
    assert "Restaurant lunch" not in body, "Restaurant lunch (Oct 21) should be excluded"
    assert "Grocery run" in body, "Grocery run (Oct 1) should appear before date_to"
    assert "Monthly bus pass" in body, "Monthly bus pass (Oct 3) should appear before date_to"
    assert "Electricity bill" in body, "Electricity bill (Oct 5) should appear before date_to"
    assert "Pharmacy" in body, "Pharmacy (Oct 7) should appear — on the boundary"


def test_date_range_filter_shows_only_in_range_transactions(client):
    """date_from=2026-10-05&date_to=2026-10-10 — only the three mid-range expenses appear."""
    _login(client)
    _seed_all_expenses(client)
    body = client.get("/profile?date_from=2026-10-05&date_to=2026-10-10").data.decode()
    # Must appear
    assert "Electricity bill" in body, "Electricity bill (Oct 5) should appear within range"
    assert "Pharmacy" in body, "Pharmacy (Oct 7) should appear within range"
    assert "Streaming subscription" in body, "Streaming subscription (Oct 10) should appear within range"
    # Must not appear
    assert "Grocery run" not in body, "Grocery run (Oct 1) should be excluded — before range"
    assert "Monthly bus pass" not in body, "Monthly bus pass (Oct 3) should be excluded — before range"
    assert "New clothing" not in body, "New clothing (Oct 14) should be excluded — after range"
    assert "Stationery" not in body, "Stationery (Oct 18) should be excluded — after range"
    assert "Restaurant lunch" not in body, "Restaurant lunch (Oct 21) should be excluded — after range"


def test_filter_label_present_when_date_from_set(client):
    """A 'Showing results' label must appear when date_from is provided."""
    _login(client)
    _seed_all_expenses(client)
    body = client.get("/profile?date_from=2026-10-05").data.decode()
    assert "Showing results" in body, "Expected 'Showing results' label when date_from is active"


def test_filter_label_present_when_date_to_set(client):
    """A 'Showing results' label must appear when date_to is provided."""
    _login(client)
    _seed_all_expenses(client)
    body = client.get("/profile?date_to=2026-10-10").data.decode()
    assert "Showing results" in body, "Expected 'Showing results' label when date_to is active"


def test_no_filter_label_when_no_params(client):
    """'Showing results' must NOT appear when no date params are passed."""
    _login(client)
    _seed_all_expenses(client)
    body = client.get("/profile").data.decode()
    assert "Showing results" not in body, "Filter label should be absent when no date params are passed"


def test_clear_link_present_when_filter_active(client):
    """A 'Clear' link must appear in the response when a date filter is active."""
    _login(client)
    _seed_all_expenses(client)
    body = client.get("/profile?date_from=2026-10-05").data.decode()
    assert "Clear" in body, "Expected a 'Clear' link when a date filter is active"


def test_clear_link_absent_when_no_filter(client):
    """A 'Clear' link must NOT appear when no date filter is applied."""
    _login(client)
    _seed_all_expenses(client)
    body = client.get("/profile").data.decode()
    assert "Clear" not in body, "Clear link should be absent when no date filter is applied"


def test_invalid_date_from_returns_200(client):
    """An invalid date_from value must not crash the app — must return HTTP 200."""
    _login(client)
    _seed_all_expenses(client)
    response = client.get("/profile?date_from=not-a-date")
    assert response.status_code == 200, "Invalid date_from should return 200, not 500"


def test_both_params_invalid_returns_200_with_all_transactions(client):
    """Both params invalid — returns 200 and all 8 transactions are visible."""
    _login(client)
    _seed_all_expenses(client)
    response = client.get("/profile?date_from=bad-date&date_to=also-bad")
    assert response.status_code == 200, "Invalid date params should not crash the app"
    body = response.data.decode()
    for _, _, _, description in _ALL_EXPENSES:
        assert description in body, f"Expected '{description}' to appear when both date params are invalid"
