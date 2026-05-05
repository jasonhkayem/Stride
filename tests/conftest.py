"""
Shared fixtures for the test suite.

The Flask test client hits the real database (same .env as dev).
Each test that creates a user gets a unique email so runs never conflict.
Cleanup deletes all rows created by the test user in dependency order.
"""
from __future__ import annotations

import uuid
import pytest

from app import create_app


# ---------------------------------------------------------------------------
# Flask test client (session-scoped — one app instance for all tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def json_headers() -> dict:
    return {"Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# User fixture — creates a fresh user, yields credentials, cleans up after
# ---------------------------------------------------------------------------

@pytest.fixture
def user(client):
    """Register a one-off user, yield credentials dict, delete everything after."""
    tag = uuid.uuid4().hex[:10]
    email = f"test_{tag}@flowtest.invalid"
    resp = client.post("/auth/signup", json={
        "name": "Flow Tester",
        "email": email,
        "password": "TestPass123!",
    })
    assert resp.status_code == 201, resp.get_json()
    data = resp.get_json()
    user_id = data["user"]["user_id"]
    token = data["token"]

    credentials = {
        "user_id": user_id,
        "token": token,
        "headers": auth_headers(token),
        "email": email,
    }
    yield credentials

    # ------------------------------------------------------------------
    # Cleanup: delete in FK dependency order so constraints are not hit
    # ------------------------------------------------------------------
    from training.db import SessionLocal
    from training.chatbot_session_messages.models import ChatbotSessionMessage
    from training.chatbot_sessions.models import ChatbotSession
    from training.training_plan_actions.models import TrainingPlanAction
    from training.training_plan_versions.models import TrainingPlanVersion
    from training.user_training_plans.models import UserTrainingPlan
    from training.activities.models import Activity
    from training.users.models import User
    from sqlalchemy import select

    uid = uuid.UUID(user_id)

    with SessionLocal() as session:
        # Messages → Sessions
        session_ids = [
            row for row in session.execute(
                select(ChatbotSession.chatbot_id).where(ChatbotSession.user_id == uid)
            ).scalars().all()
        ]
        if session_ids:
            session.query(ChatbotSessionMessage).filter(
                ChatbotSessionMessage.chatbot_id.in_(session_ids)
            ).delete(synchronize_session=False)
        session.query(ChatbotSession).filter(ChatbotSession.user_id == uid).delete()

        # Plan actions → Versions → UserTrainingPlans
        plan_ids = [
            row for row in session.execute(
                select(UserTrainingPlan.user_plan_id).where(UserTrainingPlan.user_id == uid)
            ).scalars().all()
        ]
        if plan_ids:
            version_ids = [
                row for row in session.execute(
                    select(TrainingPlanVersion.version_id).where(
                        TrainingPlanVersion.user_plan_id.in_(plan_ids)
                    )
                ).scalars().all()
            ]
            # Null out current_version_id FK before deleting versions (circular FK)
            session.query(UserTrainingPlan).filter(
                UserTrainingPlan.user_plan_id.in_(plan_ids)
            ).update({"current_version_id": None}, synchronize_session=False)
            if version_ids:
                session.query(TrainingPlanAction).filter(
                    TrainingPlanAction.version_id.in_(version_ids)
                ).delete(synchronize_session=False)
            session.query(TrainingPlanVersion).filter(
                TrainingPlanVersion.user_plan_id.in_(plan_ids)
            ).delete(synchronize_session=False)
        session.query(UserTrainingPlan).filter(UserTrainingPlan.user_id == uid).delete()

        # Activities
        session.query(Activity).filter(Activity.user_id == uid).delete()

        # User itself
        session.query(User).filter(User.user_id == uid).delete()

        session.commit()


# ---------------------------------------------------------------------------
# Canned LLM responses used by mocked tests
# ---------------------------------------------------------------------------

FAKE_PLAN_JSON = (
    '{"plan_overview":"Test 10K plan",'
    '"weeks":[{"week":1,"phase":"Base",'
    '"sessions":['
    '{"day":"Monday","type":"easy_run","distance_km":5.0,"duration_min":30,"notes":"Easy"},'
    '{"day":"Wednesday","type":"tempo","distance_km":5.0,"duration_min":30,"notes":"Tempo"},'
    '{"day":"Friday","type":"long_run","distance_km":8.0,"duration_min":50,"notes":"Long"},'
    '{"day":"Sunday","type":"interval","distance_km":6.0,"duration_min":40,"notes":"Intervals"}'
    ']}]}'
)

FAKE_SUGGEST_JSON = (
    '{"proposed_actions":[{"action":"adjust_volume","percentage":5,"scope":"next_week"}],'
    '"rationale":"You are ready to increase your weekly volume safely."}'
)

FAKE_COACH_REPLY = "## Training Feedback\n- You are doing **great**.\n- Keep it up!"
