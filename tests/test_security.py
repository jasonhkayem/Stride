"""
Flow 25 — Expired JWT → 401
Flow 26 — Malformed JWT → 401
Flow 27 — Tampered JWT → 401
Flow 28 — Wrong user's resource (ownership) → 401 or 403
Flow 29 — Health and root endpoints work unauthenticated
"""
from __future__ import annotations

import time
import uuid

import pytest

from training.auth.jwt_utils import generate_token


# ---------------------------------------------------------------------------
# Helpers — generate tokens with custom expiry
# ---------------------------------------------------------------------------

def _expired_token(user_id: str) -> str:
    """Generate a token that expired 1 second ago."""
    import base64
    import hashlib
    import hmac
    import json
    import os

    secret = os.getenv("JWT_SECRET", "dev-jwt-secret-change-in-production").encode()

    def b64enc(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    header = b64enc(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    now = int(time.time())
    payload = b64enc(json.dumps({"user_id": user_id, "role": "user", "iat": now - 7200, "exp": now - 1}, separators=(",", ":")).encode())
    signing = f"{header}.{payload}"
    sig = b64enc(hmac.new(secret, signing.encode(), hashlib.sha256).digest())
    return f"{signing}.{sig}"


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Flow 25: Expired JWT → 401
# ---------------------------------------------------------------------------

def test_expired_token_rejected(client):
    token = _expired_token(str(uuid.uuid4()))
    resp = client.post(
        "/activities",
        json={
            "user_id": str(uuid.uuid4()),
            "activity_type": "run",
            "distance": 5.0,
            "duration": 1800,
            "timestamp": "2024-01-01T08:00:00",
        },
        headers=_auth(token),
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Flow 26: Malformed JWT → 401
# ---------------------------------------------------------------------------

def test_malformed_token_rejected(client):
    for bad in ["not.a.token", "Bearer xyz", "", "x" * 50]:
        resp = client.post(
            "/activities",
            json={"user_id": str(uuid.uuid4()), "activity_type": "run",
                  "distance": 1.0, "duration": 600, "timestamp": "2024-01-01T08:00:00"},
            headers={"Authorization": f"Bearer {bad}", "Content-Type": "application/json"},
        )
        assert resp.status_code == 401, f"Expected 401 for token: {bad!r}"


# ---------------------------------------------------------------------------
# Flow 27: Tampered JWT (valid structure, bad signature) → 401
# ---------------------------------------------------------------------------

def test_tampered_token_rejected(client):
    real = generate_token(str(uuid.uuid4()), "user")
    # Flip the last character of the signature
    parts = real.split(".")
    sig = parts[2]
    flipped = sig[:-1] + ("A" if sig[-1] != "A" else "B")
    tampered = ".".join(parts[:2] + [flipped])

    resp = client.post(
        "/activities",
        json={"user_id": str(uuid.uuid4()), "activity_type": "run",
              "distance": 1.0, "duration": 600, "timestamp": "2024-01-01T08:00:00"},
        headers=_auth(tampered),
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Flow 28: Authenticated user cannot create resources for another user
# ---------------------------------------------------------------------------

def test_cannot_create_chatbot_session_for_other_user(client, user):
    other_id = str(uuid.uuid4())
    resp = client.post("/chatbot_sessions", json={
        "user_id": other_id,
        "session_type": "general",
    }, headers=user["headers"])
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Flow 29: Public endpoints are reachable without auth
# ---------------------------------------------------------------------------

def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


def test_root_endpoint(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_list_activities_no_auth(client):
    # Read-only list does not require auth
    resp = client.get("/activities")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_list_templates_no_auth(client):
    resp = client.get("/training_plan_templates")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)
