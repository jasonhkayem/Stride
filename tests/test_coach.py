"""
Flow 19 — Send a general coach message and get a reply
Flow 20 — Coach response references markdown (from mocked reply)
Flow 21 — Suggest plan changes (LLM mocked)
Flow 22 — Approve suggested changes
Flow 23 — Suggest without auth → 401
Flow 24 — Ownership enforcement: user A cannot create session for user B → 403
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from tests.conftest import FAKE_COACH_REPLY, FAKE_PLAN_JSON, FAKE_SUGGEST_JSON


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_session(client, user) -> str:
    resp = client.post("/chatbot_sessions", json={
        "user_id": user["user_id"],
        "session_type": "general",
    }, headers=user["headers"])
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["chatbot_id"]


def _get_10k_template(client) -> str:
    resp = client.get("/training_plan_templates")
    for t in resp.get_json():
        if t["goal_race"] == "10k":
            return t["template_id"]
    pytest.skip("10K template not seeded")


def _create_plan_version(client, user) -> str:
    """Return a version_id for a fresh plan (LLM mocked)."""
    template_id = _get_10k_template(client)
    plan_resp = client.post("/user_training_plans", json={
        "user_id": user["user_id"],
        "template_id": template_id,
        "start_date": "2024-06-01",
    }, headers=user["headers"])
    assert plan_resp.status_code == 201
    user_plan_id = plan_resp.get_json()["user_plan_id"]

    with patch("training.services.llm_service.LLMService.chat_completion", return_value=FAKE_PLAN_JSON):
        gen = client.post("/training_plan_versions/generate_from_template", json={
            "user_plan_id": user_plan_id,
            "template_id": template_id,
            "goal_time": "50:00",
        }, headers=user["headers"])
    assert gen.status_code == 201
    return gen.get_json()["version"]["version_id"]


# ---------------------------------------------------------------------------
# Flow 19: Send a message and receive a reply
# ---------------------------------------------------------------------------

def test_coach_reply(client, user):
    session_id = _create_session(client, user)

    with patch("training.services.llm_service.LLMService.chat_completion", return_value=FAKE_COACH_REPLY):
        resp = client.post(
            f"/chatbot_sessions/{session_id}/reply",
            json={"user_message": "How should I pace my long run?"},
            headers=user["headers"],
        )

    data = resp.get_json()
    assert resp.status_code == 200, data
    assert "assistant_message" in data
    assert len(data["assistant_message"]) > 0


# ---------------------------------------------------------------------------
# Flow 20: Mocked reply contains markdown
# ---------------------------------------------------------------------------

def test_coach_reply_contains_markdown(client, user):
    session_id = _create_session(client, user)

    with patch("training.services.llm_service.LLMService.chat_completion", return_value=FAKE_COACH_REPLY):
        resp = client.post(
            f"/chatbot_sessions/{session_id}/reply",
            json={"user_message": "Give me feedback"},
            headers=user["headers"],
        )

    msg = resp.get_json()["assistant_message"]
    assert "##" in msg or "**" in msg or "-" in msg, "Expected markdown in assistant reply"


# ---------------------------------------------------------------------------
# Flow 21: Suggest plan changes
# ---------------------------------------------------------------------------

def test_suggest_training_plan_actions(client, user):
    session_id = _create_session(client, user)
    version_id = _create_plan_version(client, user)

    with patch("training.services.llm_service.LLMService.chat_completion", return_value=FAKE_SUGGEST_JSON):
        resp = client.post(
            f"/chatbot_sessions/{session_id}/suggest_training_plan_actions",
            json={
                "version_id": version_id,
                "user_prompt": "I feel tired — can we reduce volume next week?",
                "apply_actions": False,
            },
            headers=user["headers"],
        )

    data = resp.get_json()
    assert resp.status_code == 200, data
    assert "validated_suggestion" in data
    suggestion = data["validated_suggestion"]
    assert "proposed_actions" in suggestion
    assert "rationale" in suggestion
    assert len(suggestion["proposed_actions"]) > 0


# ---------------------------------------------------------------------------
# Flow 22: Approve suggested changes → new version created
# ---------------------------------------------------------------------------

def test_approve_suggestion_creates_new_version(client, user):
    version_id = _create_plan_version(client, user)

    resp = client.post("/training_plan_versions/apply_ai_actions", json={
        "version_id": version_id,
        "proposed_actions": [{"action": "adjust_volume", "percentage": -10, "scope": "next_week"}],
        "rationale": "Athlete reported fatigue — reduce volume to aid recovery.",
    }, headers=user["headers"])
    data = resp.get_json()
    assert resp.status_code == 201, data
    assert data["new_version"]["version_id"] != version_id


# ---------------------------------------------------------------------------
# Flow 23: Suggest without auth → 401
# ---------------------------------------------------------------------------

def test_suggest_requires_auth(client, user):
    session_id = _create_session(client, user)
    version_id = _create_plan_version(client, user)

    resp = client.post(
        f"/chatbot_sessions/{session_id}/suggest_training_plan_actions",
        json={
            "version_id": version_id,
            "user_prompt": "Reduce volume",
        },
        # no Authorization header
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Flow 24: Ownership — user A cannot create a session labelled as user B
# ---------------------------------------------------------------------------

def test_cannot_create_session_for_other_user(client, user):
    other_user_id = str(uuid.uuid4())
    resp = client.post("/chatbot_sessions", json={
        "user_id": other_user_id,
        "session_type": "general",
    }, headers=user["headers"])
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# List messages on a session
# ---------------------------------------------------------------------------

def test_list_messages_after_reply(client, user):
    session_id = _create_session(client, user)

    with patch("training.services.llm_service.LLMService.chat_completion", return_value=FAKE_COACH_REPLY):
        reply_resp = client.post(
            f"/chatbot_sessions/{session_id}/reply",
            json={"user_message": "Hello coach"},
            headers=user["headers"],
        )
    assert reply_resp.status_code == 200, reply_resp.get_json()

    resp = client.get(f"/chatbot_sessions/{session_id}/messages", headers=user["headers"])
    messages = resp.get_json()
    assert resp.status_code == 200
    assert isinstance(messages, list)
    assert len(messages) >= 1
    senders = {m["sender"] for m in messages}
    # At minimum the assistant reply must be stored; user message may share same timestamp ordering
    assert "assistant" in senders
    # Verify each message has required fields
    for msg in messages:
        assert "sender" in msg
        assert "content" in msg


# ---------------------------------------------------------------------------
# Empty session has no messages
# ---------------------------------------------------------------------------

def test_new_session_has_no_messages(client, user):
    session_id = _create_session(client, user)
    resp = client.get(f"/chatbot_sessions/{session_id}/messages", headers=user["headers"])
    assert resp.status_code == 200
    assert resp.get_json() == []
