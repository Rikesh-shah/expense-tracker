import database.db as db_module
from database.db import get_db


def test_get_register_renders_form(client):
    response = client.get("/register")
    assert response.status_code == 200
    body = response.data.decode()
    assert 'name="name"' in body
    assert 'name="email"' in body
    assert 'name="password"' in body


def test_valid_registration_redirects_to_login(client):
    response = client.post("/register", data={
        "name": "Alice",
        "email": "alice@example.com",
        "password": "secret123",
    })
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_valid_registration_creates_user_in_db(client):
    client.post("/register", data={
        "name": "Bob",
        "email": "bob@example.com",
        "password": "hunter2",
    })
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", ("bob@example.com",)).fetchone()
    conn.close()
    assert row is not None
    assert row["name"] == "Bob"
    assert row["password_hash"] != "hunter2"


def test_duplicate_email_shows_error(client):
    data = {"name": "Carol", "email": "carol@example.com", "password": "pass123"}
    client.post("/register", data=data)
    response = client.post("/register", data=data)
    assert response.status_code == 200
    assert b"already exists" in response.data


def test_empty_name_shows_error(client):
    response = client.post("/register", data={
        "name": "",
        "email": "dave@example.com",
        "password": "pass123",
    })
    assert response.status_code == 200
    assert b"required" in response.data


def test_empty_email_shows_error(client):
    response = client.post("/register", data={
        "name": "Eve",
        "email": "",
        "password": "pass123",
    })
    assert response.status_code == 200
    assert b"required" in response.data


def test_empty_password_shows_error(client):
    response = client.post("/register", data={
        "name": "Frank",
        "email": "frank@example.com",
        "password": "",
    })
    assert response.status_code == 200
    assert b"required" in response.data


def test_success_flash_on_login_page(client):
    client.post("/register", data={
        "name": "Grace",
        "email": "grace@example.com",
        "password": "pass123",
    })
    response = client.get("/login")
    assert b"Account created" in response.data
