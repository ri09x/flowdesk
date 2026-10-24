from conftest import auth_header, register


def test_register_and_me(client, alice):
    res = client.get("/api/auth/me", headers=auth_header(alice["access_token"]))
    assert res.status_code == 200
    assert res.json()["email"] == alice["email"]


def test_register_duplicate_email_conflicts(client, alice):
    res = client.post(
        "/api/auth/register",
        json={"name": "Alice2", "email": alice["email"], "password": "password-123"},
    )
    assert res.status_code == 409


def test_register_short_password_rejected(client):
    res = client.post(
        "/api/auth/register",
        json={"name": "X", "email": "x@example.com", "password": "short"},
    )
    assert res.status_code == 422


def test_login_success_and_failure(client, alice):
    ok = client.post("/api/auth/login", json={"email": alice["email"], "password": "password-123"})
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = client.post("/api/auth/login", json={"email": alice["email"], "password": "wrong-password"})
    assert bad.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=auth_header("not-a-token")).status_code == 401
