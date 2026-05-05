"""
Flow 6  — Manual activity creation
Flow 7  — Edit activity
Flow 8  — Delete activity
Flow 9  — Invalid data → 400
Flow 10 — Create without auth → 401
"""
from __future__ import annotations

import pytest


def _activity_payload(user_id: str, **overrides) -> dict:
    base = {
        "user_id": user_id,
        "activity_type": "run",
        "distance": 8.5,
        "duration": 2700,
        "timestamp": "2024-03-10T07:30:00",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Flow 6: Create a manual activity
# ---------------------------------------------------------------------------

def test_create_activity(client, user):
    resp = client.post(
        "/activities",
        json=_activity_payload(user["user_id"]),
        headers=user["headers"],
    )
    data = resp.get_json()
    assert resp.status_code == 201
    assert data["activity_type"] == "run"
    assert float(data["distance"]) == pytest.approx(8.5)
    assert data["duration"] == 2700


# ---------------------------------------------------------------------------
# Flow 7: Edit activity
# ---------------------------------------------------------------------------

def test_update_activity(client, user):
    # Create first
    create = client.post(
        "/activities",
        json=_activity_payload(user["user_id"]),
        headers=user["headers"],
    )
    assert create.status_code == 201
    activity_id = create.get_json()["activity_id"]

    # Update distance
    resp = client.patch(
        f"/activities/{activity_id}",
        json={"distance": 10.0},
        headers=user["headers"],
    )
    data = resp.get_json()
    assert resp.status_code == 200
    assert float(data["distance"]) == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Flow 8: Delete activity
# ---------------------------------------------------------------------------

def test_delete_activity(client, user):
    create = client.post(
        "/activities",
        json=_activity_payload(user["user_id"]),
        headers=user["headers"],
    )
    assert create.status_code == 201
    activity_id = create.get_json()["activity_id"]

    resp = client.delete(f"/activities/{activity_id}", headers=user["headers"])
    assert resp.status_code in (200, 204)

    # Confirm it is gone
    get = client.get(f"/activities/{activity_id}")
    assert get.status_code == 404


# ---------------------------------------------------------------------------
# Flow 9: Invalid activity data → validation error
# ---------------------------------------------------------------------------

def test_create_activity_missing_required_fields(client, user):
    resp = client.post(
        "/activities",
        json={"user_id": user["user_id"]},   # missing type, distance, duration, timestamp
        headers=user["headers"],
    )
    assert resp.status_code == 400
    assert "errors" in resp.get_json()


def test_create_activity_bad_type(client, user):
    resp = client.post(
        "/activities",
        json=_activity_payload(user["user_id"], activity_type="flying"),
        headers=user["headers"],
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Flow 10: No auth → 401
# ---------------------------------------------------------------------------

def test_create_activity_no_auth(client, user):
    resp = client.post("/activities", json=_activity_payload(user["user_id"]))
    assert resp.status_code == 401


def test_delete_activity_no_auth(client, user):
    create = client.post(
        "/activities",
        json=_activity_payload(user["user_id"]),
        headers=user["headers"],
    )
    assert create.status_code == 201
    activity_id = create.get_json()["activity_id"]

    resp = client.delete(f"/activities/{activity_id}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Flow 12: Strava sync — not connected → error (no Strava token in test DB)
# ---------------------------------------------------------------------------

def test_strava_sync_not_connected(client, user):
    resp = client.post("/activities/strava/sync", json={
        "user_id": user["user_id"],
        "per_page": 10,
        "max_pages": 1,
    })
    data = resp.get_json()
    # Expected: 400/500 or an error body — not a silent 200 with fake data
    assert resp.status_code >= 400 or "error" in data


# ---------------------------------------------------------------------------
# List and get
# ---------------------------------------------------------------------------

def test_list_activities_returns_list(client, user):
    # Create one activity
    client.post(
        "/activities",
        json=_activity_payload(user["user_id"]),
        headers=user["headers"],
    )
    resp = client.get("/activities")
    assert resp.status_code == 200
    assert isinstance(resp.get_json(), list)


def test_get_activity_not_found(client):
    import uuid
    resp = client.get(f"/activities/{uuid.uuid4()}")
    assert resp.status_code == 404
