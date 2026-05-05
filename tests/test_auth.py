"""
Flow 1 — Manual registration
Flow 2 — Manual login
Flow 3 — Wrong password → 401
Flow 4 — Duplicate email → 409
Flow 5 — Unauthenticated access to protected endpoint → 401
"""
from __future__ import annotations

import uuid
import pytest

from tests.conftest import auth_headers


# ---------------------------------------------------------------------------
# Flow 1: Successful registration
# ---------------------------------------------------------------------------

def test_signup_success(client):
    email = f"signup_{uuid.uuid4().hex[:8]}@flowtest.invalid"
    resp = client.post("/auth/signup", json={
        "name": "New User",
        "email": email,
        "password": "Pass1234!",
    })
    data = resp.get_json()
    assert resp.status_code == 201
    assert "token" in data
    assert data["user"]["email"] == email


# ---------------------------------------------------------------------------
# Flow 2: Successful login
# ---------------------------------------------------------------------------

def test_login_success(client, user):
    resp = client.post("/auth/login", json={
        "email": user["email"],
        "password": "TestPass123!",
    })
    data = resp.get_json()
    assert resp.status_code == 200
    assert "token" in data
    assert data["user"]["user_id"] == user["user_id"]


# ---------------------------------------------------------------------------
# Flow 3: Wrong password → 401
# ---------------------------------------------------------------------------

def test_login_wrong_password(client, user):
    resp = client.post("/auth/login", json={
        "email": user["email"],
        "password": "WrongPassword!",
    })
    assert resp.status_code == 401
    assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# Flow 4: Duplicate email → 409
# ---------------------------------------------------------------------------

def test_signup_duplicate_email(client, user):
    resp = client.post("/auth/signup", json={
        "name": "Duplicate",
        "email": user["email"],
        "password": "Pass1234!",
    })
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Flow 5: Unauthenticated access → 401
# ---------------------------------------------------------------------------

def test_unauthenticated_create_activity(client):
    resp = client.post("/activities", json={
        "user_id": str(uuid.uuid4()),
        "activity_type": "run",
        "distance": 5.0,
        "duration": 1800,
        "timestamp": "2024-01-01T08:00:00",
    })
    assert resp.status_code == 401


def test_unauthenticated_create_chatbot_session(client):
    resp = client.post("/chatbot_sessions", json={
        "user_id": str(uuid.uuid4()),
        "session_type": "general",
    })
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Flow 2b: /auth/me returns correct user
# ---------------------------------------------------------------------------

def test_me_returns_user(client, user):
    resp = client.get(f"/auth/me/{user['user_id']}")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["user_id"] == user["user_id"]
    assert data["email"] == user["email"]


def test_me_unknown_user(client):
    resp = client.get(f"/auth/me/{uuid.uuid4()}")
    assert resp.status_code == 404
