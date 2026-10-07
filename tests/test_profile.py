import re


def _login(client, name="Alice", email="alice@example.com", password="pass123"):
    client.post("/register", data={"name": name, "email": email, "password": password})
    client.post("/login",    data={"email": email, "password": password})


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
    assert "Priya Sharma" in body
    assert "priya.sharma@example.com" in body
    assert "January 2024" in body


def test_profile_shows_stats(client):
    _login(client)
    body = client.get("/profile").data.decode()
    assert "12,450" in body
    assert "38" in body
    assert "Food" in body


def test_profile_shows_transaction_table(client):
    _login(client)
    body = client.get("/profile").data.decode()
    assert "Swiggy" in body
    assert "Metro card recharge" in body
    assert "Amazon" in body
    assert "Electricity bill" in body


def test_profile_shows_category_breakdown(client):
    _login(client)
    body = client.get("/profile").data.decode()
    assert "Shopping" in body
    assert "Utilities" in body
    assert "Transport" in body


def test_profile_has_no_hex_colours(client):
    _login(client)
    body = client.get("/profile").data.decode()
    hex_pattern = re.compile(r'#[0-9a-fA-F]{3,6}\b')
    assert not hex_pattern.search(body), "Hex colour found in rendered profile HTML"
