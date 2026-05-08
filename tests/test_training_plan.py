"""
Flow 13 — Generate training plan from template
Flow 14 — Session type formatting data (easy_run, tempo, long_run present in snapshot)
Flow 15 — Multi-week structure in snapshot
Flow 16 — Competitive goal → realistic session volume (≥4 sessions/week)
Flow 17 — Approve AI-suggested actions (apply_ai_actions)
Flow 18 — Decline: validate_ai_actions rejects bad data
"""
from __future__ import annotations

import datetime
import json
from unittest.mock import patch

import pytest

from tests.conftest import FAKE_PLAN_JSON, FAKE_SUGGEST_JSON


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_10k_template(client) -> str:
    """Return the template_id for the 10K plan."""
    resp = client.get("/training_plan_templates")
    assert resp.status_code == 200
    templates = resp.get_json()
    for t in templates:
        if t["goal_race"] == "10k":
            return t["template_id"]
    pytest.skip("10K template not seeded — run scripts/seed_training_plan_templates.py")


def _create_user_plan(client, user, template_id) -> str:
    """Create a UserTrainingPlan and return its user_plan_id."""
    resp = client.post("/user_training_plans", json={
        "user_id": user["user_id"],
        "template_id": template_id,
        "start_date": datetime.date.today().isoformat(),
    }, headers=user["headers"])
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["user_plan_id"]


# ---------------------------------------------------------------------------
# Flow 13: Generate a plan from the 10K template (LLM mocked)
# ---------------------------------------------------------------------------

def test_generate_from_template(client, user):
    template_id = _get_10k_template(client)
    user_plan_id = _create_user_plan(client, user, template_id)

    with patch("training.services.llm_service.LLMService.chat_completion", return_value=FAKE_PLAN_JSON):
        resp = client.post("/training_plan_versions/generate_from_template", json={
            "user_plan_id": user_plan_id,
            "template_id": template_id,
            "goal_time": "50:00",
        }, headers=user["headers"])

    data = resp.get_json()
    assert resp.status_code == 201, data
    snap = data["plan_snapshot"]
    assert snap["goal_race"] == "10k"
    assert snap["goal_time"] == "50:00"
    assert "weeks" in snap
    assert len(snap["weeks"]) > 0


# ---------------------------------------------------------------------------
# Flow 14: Session types are stored in raw form in the snapshot
#          (easy_run, tempo, long_run — UI formats them, DB stores raw)
# ---------------------------------------------------------------------------

def test_snapshot_contains_session_types(client, user):
    template_id = _get_10k_template(client)
    user_plan_id = _create_user_plan(client, user, template_id)

    with patch("training.services.llm_service.LLMService.chat_completion", return_value=FAKE_PLAN_JSON):
        resp = client.post("/training_plan_versions/generate_from_template", json={
            "user_plan_id": user_plan_id,
            "template_id": template_id,
            "goal_time": "50:00",
        }, headers=user["headers"])

    assert resp.status_code == 201
    snap = resp.get_json()["plan_snapshot"]
    sessions = snap["weeks"][0]["sessions"]
    types = {s["type"] for s in sessions}
    assert "easy_run" in types
    assert "tempo" in types
    assert "long_run" in types


# ---------------------------------------------------------------------------
# Flow 15: Snapshot contains multiple weeks
# ---------------------------------------------------------------------------

def test_snapshot_has_multi_week_structure(client, user):
    template_id = _get_10k_template(client)
    user_plan_id = _create_user_plan(client, user, template_id)

    # Build a fake plan with 3 weeks
    fake_multi = json.dumps({
        "plan_overview": "3-week test plan",
        "weeks": [
            {"week": i, "phase": "Base", "sessions": [
                {"day": "Monday", "type": "easy_run", "distance_km": 5.0, "duration_min": 30, "notes": "Easy"},
            ]}
            for i in range(1, 4)
        ],
    })

    with patch("training.services.llm_service.LLMService.chat_completion", return_value=fake_multi):
        resp = client.post("/training_plan_versions/generate_from_template", json={
            "user_plan_id": user_plan_id,
            "template_id": template_id,
            "goal_time": "50:00",
        }, headers=user["headers"])

    assert resp.status_code == 201
    weeks = resp.get_json()["plan_snapshot"]["weeks"]
    assert len(weeks) == 3


# ---------------------------------------------------------------------------
# Flow 16: Competitive goal time → ≥4 sessions/week
# ---------------------------------------------------------------------------

def test_competitive_goal_produces_high_volume(client, user):
    template_id = _get_10k_template(client)
    user_plan_id = _create_user_plan(client, user, template_id)

    # 35:00 for 10K ≈ 3:30/km base pace → competitive → should produce ≥4 sessions/week
    # Capture the prompt to verify min_runs_per_week
    captured = {}

    def fake_llm(messages, **kwargs):
        captured["prompt"] = messages[-1]["content"]
        return FAKE_PLAN_JSON

    with patch("training.services.llm_service.LLMService.chat_completion", side_effect=fake_llm):
        resp = client.post("/training_plan_versions/generate_from_template", json={
            "user_plan_id": user_plan_id,
            "template_id": template_id,
            "goal_time": "35:00",
        }, headers=user["headers"])

    assert resp.status_code == 201
    snap = resp.get_json()["plan_snapshot"]
    assert snap["min_runs_per_week"] >= 4, (
        f"Expected ≥4 sessions/week for sub-35:00 10K goal, got {snap['min_runs_per_week']}"
    )


# ---------------------------------------------------------------------------
# Flow 17: Apply AI-suggested actions creates a new version
# ---------------------------------------------------------------------------

def test_apply_ai_actions(client, user):
    template_id = _get_10k_template(client)
    user_plan_id = _create_user_plan(client, user, template_id)

    with patch("training.services.llm_service.LLMService.chat_completion", return_value=FAKE_PLAN_JSON):
        gen = client.post("/training_plan_versions/generate_from_template", json={
            "user_plan_id": user_plan_id,
            "template_id": template_id,
            "goal_time": "50:00",
        }, headers=user["headers"])
    assert gen.status_code == 201
    version_id = gen.get_json()["version"]["version_id"]

    resp = client.post("/training_plan_versions/apply_ai_actions", json={
        "version_id": version_id,
        "proposed_actions": [{"action": "adjust_volume", "percentage": 5, "scope": "next_week"}],
        "rationale": "Athlete is ready to increase training load safely.",
    }, headers=user["headers"])
    data = resp.get_json()
    assert resp.status_code == 201, data
    assert "new_version" in data
    assert data["new_version"]["created_by"] == "ai"


# ---------------------------------------------------------------------------
# Flow 18: apply_ai_actions rejects invalid action data → 400
# ---------------------------------------------------------------------------

def test_apply_ai_actions_invalid_action(client, user):
    template_id = _get_10k_template(client)
    user_plan_id = _create_user_plan(client, user, template_id)

    with patch("training.services.llm_service.LLMService.chat_completion", return_value=FAKE_PLAN_JSON):
        gen = client.post("/training_plan_versions/generate_from_template", json={
            "user_plan_id": user_plan_id,
            "template_id": template_id,
            "goal_time": "50:00",
        }, headers=user["headers"])
    version_id = gen.get_json()["version"]["version_id"]

    resp = client.post("/training_plan_versions/apply_ai_actions", json={
        "version_id": version_id,
        "proposed_actions": [{"action": "do_magic"}],   # invalid action type
        "rationale": "Short",                            # too short rationale
    }, headers=user["headers"])
    assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# Templates endpoint returns all 4 races
# ---------------------------------------------------------------------------

def test_list_templates_returns_all_races(client):
    resp = client.get("/training_plan_templates")
    assert resp.status_code == 200
    races = {t["goal_race"] for t in resp.get_json()}
    assert {"5k", "10k", "half_marathon", "marathon"}.issubset(races), (
        "Seed the DB first: python scripts/seed_training_plan_templates.py"
    )
