"""Signup, login, recovery, and access control."""

from itertools import count

_phones = count(9000000000)


def _signup(client, email, password, name="Saurabh Singh", phone=None):
    return client.post(
        "/api/auth/signup",
        json={
            "full_name": name,
            "email": email,
            "country_iso": "IN",
            "dial_code": "+91",
            "phone_number": phone or str(next(_phones)),
            "password": password,
            "confirm_password": password,
        },
    )


def test_signup_login_and_me(client, strong_password):
    created = _signup(client, "saurabh@example.com", strong_password)
    assert created.status_code == 201
    body = created.json()
    assert body["email"] == "saurabh@example.com"
    assert body["full_name"] == "Saurabh Singh"
    assert body["country_iso"] == "IN"
    assert body["dial_code"] == "+91"
    assert body["phone_e164"] == f"+91{body['phone_number']}"
    assert "password" not in body

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["id"] == body["id"]

    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401

    logged_in = client.post(
        "/api/auth/login",
        json={"email": "saurabh@example.com", "password": strong_password, "remember_me": True},
    )
    assert logged_in.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_duplicate_email_and_weak_password(client, strong_password):
    assert _signup(client, "dup@example.com", strong_password).status_code == 201
    duplicate = _signup(client, "dup@example.com", strong_password)
    assert duplicate.status_code == 409

    weak = client.post(
        "/api/auth/signup",
        json={
            "full_name": "Saurabh Singh",
            "email": "weak@example.com",
            "country_iso": "IN",
            "dial_code": "+91",
            "phone_number": "9876543210",
            "password": "password",
            "confirm_password": "password",
        },
    )
    assert weak.status_code == 422
    assert "uppercase" in weak.json()["detail"].lower() or "digit" in weak.json()["detail"].lower()


def test_invalid_login_and_unauthorized_puzzle_access(client, strong_password):
    _signup(client, "user@example.com", strong_password)
    client.post("/api/auth/logout")
    bad = client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "WrongPass1!", "remember_me": False},
    )
    assert bad.status_code == 401
    missing = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "WrongPass1!", "remember_me": False},
    )
    assert missing.status_code == 401
    assert client.get("/api/puzzles").status_code == 401
    assert client.get("/api/puzzles/stats").status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_password_reset_flow(client, strong_password):
    _signup(client, "reset@example.com", strong_password)
    forgotten = client.post("/api/auth/forgot-password", json={"email": "reset@example.com"})
    assert forgotten.status_code == 200
    token = forgotten.json()["reset_token"]
    assert token
    unknown = client.post("/api/auth/forgot-password", json={"email": "missing@example.com"})
    assert unknown.status_code == 200
    assert unknown.json()["reset_token"] is None

    updated = "NewValidPass2!"
    reset = client.post(
        "/api/auth/reset-password",
        json={"token": token, "password": updated, "confirm_password": updated},
    )
    assert reset.status_code == 200
    client.post("/api/auth/logout")
    old = client.post(
        "/api/auth/login",
        json={"email": "reset@example.com", "password": strong_password, "remember_me": False},
    )
    assert old.status_code == 401
    new = client.post(
        "/api/auth/login",
        json={"email": "reset@example.com", "password": updated, "remember_me": False},
    )
    assert new.status_code == 200


def test_profile_and_change_password(client, strong_password):
    _signup(client, "profile@example.com", strong_password)
    renamed = client.patch("/api/auth/me", json={"full_name": "Saurabh K."})
    assert renamed.status_code == 200
    assert renamed.json()["full_name"] == "Saurabh K."
    changed = client.post(
        "/api/auth/change-password",
        json={
            "current_password": strong_password,
            "password": "ChangedPass3!",
            "confirm_password": "ChangedPass3!",
        },
    )
    assert changed.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_phone_country_and_duplicate_number(client, strong_password):
    countries = client.get("/api/auth/countries")
    assert countries.status_code == 200
    india = next(item for item in countries.json() if item["iso"] == "IN")
    assert india["dial"] == "+91"
    assert india["min"] == 10

    created = _signup(client, "phone@example.com", strong_password, phone="9876543210")
    assert created.status_code == 201
    assert created.json()["phone_e164"] == "+919876543210"

    taken = _signup(client, "other-phone@example.com", strong_password, phone="9876543210")
    assert taken.status_code == 409
    assert "phone" in taken.json()["detail"].lower()

    unknown = client.post(
        "/api/auth/signup",
        json={
            "full_name": "Saurabh Singh",
            "email": "bad-country@example.com",
            "country_iso": "ZZ",
            "dial_code": "+99",
            "phone_number": "1234567890",
            "password": strong_password,
            "confirm_password": strong_password,
        },
    )
    assert unknown.status_code == 422

    short = client.post(
        "/api/auth/signup",
        json={
            "full_name": "Saurabh Singh",
            "email": "short-phone@example.com",
            "country_iso": "IN",
            "dial_code": "+91",
            "phone_number": "12345",
            "password": strong_password,
            "confirm_password": strong_password,
        },
    )
    assert short.status_code == 422


def test_login_rate_limit(client, strong_password, monkeypatch):
    monkeypatch.setenv("LOGIN_MAX_ATTEMPTS", "3")
    from app.core.config import get_settings

    get_settings.cache_clear()
    _signup(client, "limit@example.com", strong_password)
    client.post("/api/auth/logout")
    for _ in range(3):
        response = client.post(
            "/api/auth/login",
            json={"email": "limit@example.com", "password": "WrongPass1!", "remember_me": False},
        )
        assert response.status_code == 401
    blocked = client.post(
        "/api/auth/login",
        json={"email": "limit@example.com", "password": strong_password, "remember_me": False},
    )
    assert blocked.status_code == 429
