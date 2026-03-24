from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select

from training.db import SessionLocal

from .models import UserIntegration


class UserIntegrationService:
    def get_strava_for_user(self, user_id):
        with SessionLocal() as session:
            stmt = select(UserIntegration).where(
                UserIntegration.user_id == user_id,
                UserIntegration.provider == "strava",
            )
            return session.execute(stmt).scalar_one_or_none()

    def upsert_strava_for_user(
        self,
        user_id,
        external_user_id: str,
        access_token: str,
        refresh_token: Optional[str],
        token_expires_at: Optional[datetime],
        scopes: Optional[str],
    ) -> UserIntegration:
        with SessionLocal() as session:
            stmt = select(UserIntegration).where(
                UserIntegration.user_id == user_id,
                UserIntegration.provider == "strava",
            )
            item = session.execute(stmt).scalar_one_or_none()
            if item is None:
                item = UserIntegration(
                    user_id=user_id,
                    provider="strava",
                    external_user_id=external_user_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expires_at=token_expires_at,
                    scopes=scopes,
                )
                session.add(item)
            else:
                item.external_user_id = external_user_id
                item.access_token = access_token
                item.refresh_token = refresh_token
                item.token_expires_at = token_expires_at
                item.scopes = scopes

            session.commit()
            session.refresh(item)
            return item

    def delete_strava_for_user(self, user_id) -> bool:
        with SessionLocal() as session:
            stmt = select(UserIntegration).where(
                UserIntegration.user_id == user_id,
                UserIntegration.provider == "strava",
            )
            item = session.execute(stmt).scalar_one_or_none()
            if item is None:
                return False
            session.delete(item)
            session.commit()
            return True
