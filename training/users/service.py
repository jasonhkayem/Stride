from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from training.common.crud_service import CRUDService
from training.completed_actions.models import CompletedAction
from training.completed_actions.schemas import CompletedActionSchema
from training.chatbot_sessions.models import ChatbotSession
from training.chatbot_sessions.schemas import ChatbotSessionSchema
from training.services.strava_oauth_service import StravaOAuthError, StravaOAuthService
from training.user_integrations.models import UserIntegration
from training.user_training_plans.models import UserTrainingPlan
from training.user_training_plans.schemas import UserTrainingPlanSchema
from training.db import SessionLocal

from .models import User


class UserService(CRUDService):
    def __init__(self):
        super().__init__(User, "user_id")
        self.strava_oauth_service = StravaOAuthService()

    def _to_datetime_utc_naive(self, epoch_seconds: Optional[int]) -> Optional[datetime]:
        if epoch_seconds is None:
            return None
        try:
            return datetime.fromtimestamp(int(epoch_seconds), tz=timezone.utc).replace(tzinfo=None)
        except (TypeError, ValueError):
            return None

    def get_with_related(self, user_id: str) -> Optional[Dict[str, Any]]:
        with SessionLocal() as session:
            user = self.get_by_id(user_id)
            if user is None:
                return None

            user_schema = __import__("training.users.schemas", fromlist=["UserSchema"]).UserSchema()
            plans = list(
                session.execute(
                    select(UserTrainingPlan).where(UserTrainingPlan.user_id == user.user_id)
                ).scalars().all()
            )
            completed_actions = list(
                session.execute(
                    select(CompletedAction).where(CompletedAction.user_id == user.user_id)
                ).scalars().all()
            )
            sessions = list(
                session.execute(
                    select(ChatbotSession).where(ChatbotSession.user_id == user.user_id)
                ).scalars().all()
            )

            result = user_schema.dump(user)
            result["user_training_plans"] = UserTrainingPlanSchema().dump(plans, many=True)
            result["completed_actions"] = CompletedActionSchema().dump(completed_actions, many=True)
            result["chatbot_sessions"] = ChatbotSessionSchema().dump(sessions, many=True)
            return result

    def list_all_with_related(self) -> List[Dict[str, Any]]:
        users = self.list_all()
        results: List[Dict[str, Any]] = []
        for user in users:
            related = self.get_with_related(str(user.user_id))
            if related is not None:
                results.append(related)
        return results

    def search_by_username(self, query: str, limit: int = 10) -> List[User]:
        q = (query or "").strip()
        if not q:
            return []

        safe_limit = max(1, min(limit, 50))
        with SessionLocal() as session:
            results = (
                session.execute(
                    select(User)
                    .where(User.username.isnot(None))
                    .where(User.username.ilike(f"%{q}%"))
                    .order_by(User.username.asc())
                    .limit(safe_limit)
                )
                .scalars()
                .all()
            )
            return list(results)

    def get_strava_authorize_url(self, user_id: str) -> Dict[str, str]:
        user = self.get_by_id(user_id)
        if user is None:
            raise ValueError("user not found")
        return {"authorize_url": self.strava_oauth_service.build_authorize_url(user_id=user_id)}

    def get_strava_connection(self, user_id: str) -> Dict[str, Any]:
        with SessionLocal() as session:
            uid = self._coerce_pk(user_id)
            user = session.execute(select(User).where(User.user_id == uid)).scalar_one_or_none()
            if user is None:
                raise ValueError("user not found")

            integration = session.execute(
                select(UserIntegration).where(
                    UserIntegration.user_id == uid,
                    UserIntegration.provider == "strava",
                )
            ).scalar_one_or_none()

            return {
                "connected": integration is not None,
                "strava_athlete_id": user.strava_athlete_id,
                "strava_connected_at": user.strava_connected_at,
            }

    def connect_strava_oauth(self, user_id: str, code: str, state: str) -> Dict[str, Any]:
        if not code:
            raise ValueError("code is required")
        if not state:
            raise ValueError("state is required")

        state_user_id = self.strava_oauth_service.validate_state(state)
        if str(state_user_id) != str(user_id):
            raise ValueError("OAuth state does not match user")

        token_payload = self.strava_oauth_service.exchange_code(code)
        access_token = token_payload.get("access_token")
        refresh_token = token_payload.get("refresh_token")
        expires_at = self._to_datetime_utc_naive(token_payload.get("expires_at"))
        scope = token_payload.get("scope")

        athlete_payload = token_payload.get("athlete") or self.strava_oauth_service.fetch_athlete(access_token)
        athlete_id = athlete_payload.get("id")
        if athlete_id is None:
            raise StravaOAuthError("Strava OAuth response missing athlete id")

        with SessionLocal() as session:
            uid = self._coerce_pk(user_id)
            user = session.execute(select(User).where(User.user_id == uid)).scalar_one_or_none()
            if user is None:
                raise ValueError("user not found")

            # If another account already holds this athlete_id, clear it first.
            # Flush immediately so the unique constraint is released before we assign
            # the athlete_id to the current user — SQLAlchemy would otherwise batch
            # both UPDATEs and execute them in an order that violates the constraint.
            other = session.execute(
                select(User).where(User.strava_athlete_id == str(athlete_id), User.user_id != uid)
            ).scalar_one_or_none()
            if other is not None:
                other.strava_athlete_id = None
                other.strava_connected_at = None
                session.flush()

            user.strava_athlete_id = str(athlete_id)
            user.strava_connected_at = datetime.utcnow()

            integration = session.execute(
                select(UserIntegration).where(
                    UserIntegration.user_id == uid,
                    UserIntegration.provider == "strava",
                )
            ).scalar_one_or_none()
            if integration is None:
                integration = UserIntegration(
                    user_id=uid,
                    provider="strava",
                    external_user_id=str(athlete_id),
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expires_at=expires_at,
                    scopes=scope,
                )
                session.add(integration)
            else:
                integration.external_user_id = str(athlete_id)
                integration.access_token = access_token
                integration.refresh_token = refresh_token
                integration.token_expires_at = expires_at
                integration.scopes = scope

            session.commit()
            session.refresh(user)

            return {
                "connected": True,
                "user_id": str(user.user_id),
                "strava_athlete_id": user.strava_athlete_id,
                "strava_connected_at": user.strava_connected_at,
            }

    def connect_strava_oauth_from_state(self, code: str, state: str) -> Dict[str, Any]:
        user_id = self.strava_oauth_service.validate_state(state)
        return self.connect_strava_oauth(user_id=str(user_id), code=code, state=state)

    def disconnect_strava(self, user_id: str) -> Dict[str, Any]:
        with SessionLocal() as session:
            uid = self._coerce_pk(user_id)
            user = session.execute(select(User).where(User.user_id == uid)).scalar_one_or_none()
            if user is None:
                raise ValueError("user not found")

            integration = session.execute(
                select(UserIntegration).where(
                    UserIntegration.user_id == uid,
                    UserIntegration.provider == "strava",
                )
            ).scalar_one_or_none()
            if integration is not None:
                session.delete(integration)

            user.strava_athlete_id = None
            user.strava_connected_at = None
            session.commit()
            return {"connected": False}
