import re
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
