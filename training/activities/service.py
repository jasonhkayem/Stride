from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select

from training.common.crud_service import CRUDService
from training.db import SessionLocal
from training.services.strava_oauth_service import StravaOAuthError, StravaOAuthService
from training.user_integrations.models import UserIntegration

from .models import Activity


class ActivitySyncError(Exception):
    """Raised when syncing activities from Strava fails."""


class ActivityService(CRUDService):
    def __init__(self):
        super().__init__(Activity, "activity_id")
        self.strava_oauth_service = StravaOAuthService()

    @staticmethod
    def _normalize_activity_type(strava_type: Optional[str]) -> Optional[str]:
        if not strava_type:
            return None

        normalized = str(strava_type).strip().lower()
        mapping = {
            "run": "run",
            "virtualrun": "run",
            "ride": "bike",
            "virtualride": "bike",
            "ebikeride": "bike",
            "swim": "swim",
        }
        return mapping.get(normalized)

    @staticmethod
    def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None

        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    def sync_from_strava(
        self,
        user_id: str,
        per_page: int = 30,
        page: int = 1,
        max_pages: int = 1,
        before: Optional[int] = None,
        after: Optional[int] = None,
    ) -> Dict[str, Any]:
        if per_page < 1 or per_page > 200:
            raise ActivitySyncError("per_page must be between 1 and 200")
        if page < 1:
            raise ActivitySyncError("page must be >= 1")
        if max_pages < 1 or max_pages > 20:
            raise ActivitySyncError("max_pages must be between 1 and 20")

        uid = self._coerce_pk(user_id)

        with SessionLocal() as session:
            integration = session.execute(
                select(UserIntegration).where(
                    UserIntegration.user_id == uid,
                    UserIntegration.provider == "strava",
                )
            ).scalar_one_or_none()
            if integration is None:
                raise ActivitySyncError("Strava is not connected for this user")

            existing_strava_ids = {
                value
                for value in session.execute(
                    select(Activity.strava_id).where(
                        Activity.user_id == uid,
                        Activity.strava_id.is_not(None),
                    )
                ).scalars().all()
                if value
            }

            imported = 0
            skipped_existing = 0
            skipped_unsupported = 0
            skipped_invalid = 0
            current_page = page
            pages_scanned = 0

            for _ in range(max_pages):
                try:
                    rows = self.strava_oauth_service.fetch_activities(
                        access_token=integration.access_token,
                        before=before,
                        after=after,
                        page=current_page,
                        per_page=per_page,
                    )
                except StravaOAuthError as exc:
                    raise ActivitySyncError(str(exc)) from exc

                pages_scanned += 1
                if not rows:
                    break

                for row in rows:
                    strava_id_raw = row.get("id")
                    if strava_id_raw in (None, ""):
                        skipped_invalid += 1
                        continue

                    strava_id = str(strava_id_raw)
                    if strava_id in existing_strava_ids:
                        skipped_existing += 1
                        continue

                    activity_type = self._normalize_activity_type(row.get("type"))
                    if activity_type is None:
                        skipped_unsupported += 1
                        continue

                    timestamp = self._parse_timestamp(
                        row.get("start_date") or row.get("start_date_local")
                    )
                    distance_m = row.get("distance")
                    moving_time = row.get("moving_time")

                    try:
                        distance_km = float(distance_m) / 1000.0
                        duration_sec = int(moving_time)
                    except (TypeError, ValueError):
                        skipped_invalid += 1
                        continue

                    if timestamp is None or distance_km < 0 or duration_sec < 0:
                        skipped_invalid += 1
                        continue

                    session.add(
                        Activity(
                            user_id=uid,
                            strava_id=strava_id,
                            activity_type=activity_type,
                            distance=round(distance_km, 3),
                            duration=duration_sec,
                            timestamp=timestamp,
                        )
                    )
                    existing_strava_ids.add(strava_id)
                    imported += 1

                if len(rows) < per_page:
                    break
                current_page += 1

            session.commit()

            return {
                "user_id": str(uid),
                "imported": imported,
                "skipped_existing": skipped_existing,
                "skipped_unsupported": skipped_unsupported,
                "skipped_invalid": skipped_invalid,
                "pages_scanned": pages_scanned,
            }
