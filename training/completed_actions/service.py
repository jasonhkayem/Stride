from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from training.completed_action_laps.models import CompletedActionLap
from training.db import SessionLocal
from training.training_plan_actions.models import TrainingPlanAction
from training.training_plan_versions.models import TrainingPlanVersion
from training.user_training_plans.models import UserTrainingPlan

from .models import CompletedAction


class CompletedActionNotFoundError(Exception):
    """Raised when a completed action cannot be found."""


class CompletedActionValidationError(Exception):
    """Raised when payload validation fails."""


class CompletedActionService:
    """Business logic for completed actions and Strava ingestion."""

    @staticmethod
    def _to_uuid(value: Optional[str], field_name: str) -> Optional[uuid.UUID]:
        if value is None:
            return None
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError) as exc:
            raise CompletedActionValidationError(f"{field_name} must be a valid UUID") from exc

    @staticmethod
    def _resolve_training_plan_action_id(session, user_id: uuid.UUID) -> Optional[uuid.UUID]:
        stmt = (
            select(TrainingPlanAction.action_id)
            .join(TrainingPlanVersion, TrainingPlanVersion.version_id == TrainingPlanAction.version_id)
            .join(UserTrainingPlan, UserTrainingPlan.user_plan_id == TrainingPlanVersion.user_plan_id)
            .where(UserTrainingPlan.user_id == user_id)
            .order_by(TrainingPlanAction.applied_at.desc())
            .limit(1)
        )
        return session.execute(stmt).scalar_one_or_none()

    @staticmethod
    def _km_from_meters(meters: Any) -> Decimal:
        if meters is None:
            return Decimal("0.00")
        km = Decimal(str(meters)) / Decimal("1000")
        return km.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _minutes_from_seconds(seconds: Any) -> int:
        if seconds is None:
            return 0
        return max(0, int(round(float(seconds) / 60.0)))

    @staticmethod
    def _pace_sec_per_km(distance_m: Any, moving_time_sec: Any) -> int:
        try:
            distance = float(distance_m or 0)
            moving_time = float(moving_time_sec or 0)
        except (TypeError, ValueError):
            return 0

        if distance <= 0 or moving_time <= 0:
            return 0

        return int(round(moving_time / (distance / 1000.0)))

    @staticmethod
    def _parse_datetime(value: Any, field_name: str) -> datetime:
        if not value:
            raise CompletedActionValidationError(f"{field_name} is required")
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            raise CompletedActionValidationError(f"{field_name} must be an ISO datetime string")

        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise CompletedActionValidationError(f"{field_name} must be a valid ISO datetime") from exc
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    @staticmethod
    def _normalize_action_type(value: Any) -> str:
        raw = str(value or "run").strip().lower()
        mapping = {
            "run": "run",
            "ride": "bike",
            "virtualride": "bike",
            "ebikeride": "bike",
            "swim": "swim",
        }
        normalized = mapping.get(raw)
        if normalized is None:
            raise CompletedActionValidationError(
                "Unsupported Strava activity type for completed_actions: " + raw
            )
        return normalized

    def _build_lap_payload(
        self,
        completed_action_id: uuid.UUID,
        lap: Dict[str, Any],
        index: int,
    ) -> Dict[str, Any]:
        distance_m = lap.get("distance")
        moving_time_sec = lap.get("moving_time")
        return {
            "completed_action_id": completed_action_id,
            "lap_index": int(lap.get("lap_index", index)),
            "distance_km": self._km_from_meters(distance_m),
            "moving_time_min": (Decimal(str(moving_time_sec or 0)) / Decimal("60")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ),
            "avg_pace_sec_per_km": int(
                lap.get(
                    "avg_pace_sec_per_km",
                    self._pace_sec_per_km(distance_m=distance_m, moving_time_sec=moving_time_sec),
                )
                or 0
            ),
            "avg_heart_rate": lap.get("avg_heart_rate", lap.get("average_heartrate")),
            "elevation_gain_m": lap.get("elevation_gain_m", lap.get("total_elevation_gain")),
        }

    def create_laps(
        self,
        session,
        completed_action_id: uuid.UUID,
        laps_payload: List[Dict[str, Any]],
    ) -> List[CompletedActionLap]:
        laps: List[CompletedActionLap] = []
        for index, lap in enumerate(laps_payload, start=1):
            lap_data = dict(lap)
            lap_data["completed_action_id"] = completed_action_id
            lap_data.setdefault("lap_index", index)
            lap_obj = CompletedActionLap(**lap_data)
            session.add(lap_obj)
            laps.append(lap_obj)
        return laps

    def create(self, payload: Dict[str, Any]) -> CompletedAction:
        with SessionLocal() as session:
            data = dict(payload)
            laps_payload = data.pop("laps", [])

            item = CompletedAction(**data)
            session.add(item)
            session.flush()

            if laps_payload:
                self.create_laps(session, item.id, laps_payload)

            session.commit()

            stmt = (
                select(CompletedAction)
                .options(selectinload(CompletedAction.laps))
                .where(CompletedAction.id == item.id)
            )
            return session.execute(stmt).scalar_one()

    def create_from_strava_activity(self, payload: Dict[str, Any]) -> Tuple[CompletedAction, bool]:
        """
        Create a completed action from Strava activity payload.

        Accepted formats:
        1) {"user_id": "...", "training_plan_action_id": "...", "activity": {...strava...}}
        2) top-level Strava fields with required "user_id".
        """
        activity = payload.get("activity") if isinstance(payload.get("activity"), dict) else payload

        user_id = self._to_uuid(payload.get("user_id"), "user_id")
        if user_id is None:
            raise CompletedActionValidationError("user_id is required")

        explicit_training_plan_action_id = self._to_uuid(
            payload.get("training_plan_action_id"), "training_plan_action_id"
        )

        distance_m = activity.get("distance", 0)
        moving_time_sec = activity.get("moving_time", activity.get("elapsed_time", 0))
        pace_sec_per_km = self._pace_sec_per_km(distance_m=distance_m, moving_time_sec=moving_time_sec)

        map_obj = activity.get("map") if isinstance(activity.get("map"), dict) else {}
        route_polyline = map_obj.get("summary_polyline") or activity.get("route_polyline") or ""
        completed_at = self._parse_datetime(
            activity.get("start_date") or activity.get("start_date_local"),
            "completed_at",
        )

        strava_activity_id = activity.get("id")
        if strava_activity_id in (None, ""):
            raise CompletedActionValidationError("Strava activity id is required")

        with SessionLocal() as session:
            resolved_action_id = explicit_training_plan_action_id or self._resolve_training_plan_action_id(
                session=session,
                user_id=user_id,
            )
            if resolved_action_id is None:
                raise CompletedActionValidationError(
                    "training_plan_action_id was not provided and could not be auto-mapped"
                )

            existing = session.execute(
                select(CompletedAction)
                .options(selectinload(CompletedAction.laps))
                .where(
                    CompletedAction.user_id == user_id,
                    CompletedAction.strava_activity_id == int(strava_activity_id),
                )
                .order_by(CompletedAction.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            if existing is not None:
                return existing, False

            completed_payload: Dict[str, Any] = {
                "user_id": user_id,
                "training_plan_action_id": resolved_action_id,
                "strava_activity_id": int(strava_activity_id),
                "name": activity.get("name") or "Strava Activity",
                "action_type": self._normalize_action_type(activity.get("type")),
                "actual_distance_km": self._km_from_meters(distance_m),
                "actual_duration_min": self._minutes_from_seconds(moving_time_sec),
                "avg_pace_sec_per_km": pace_sec_per_km,
                "avg_heart_rate": activity.get("average_heartrate"),
                "elevation_gain_m": activity.get("total_elevation_gain"),
                "calories": activity.get("calories"),
                "gear_id": activity.get("gear_id"),
                "manual_entry": False,
                "completed_at": completed_at,
                "route_polyline": route_polyline,
            }

            missing = [
                field
                for field in ("completed_at", "route_polyline", "name", "action_type")
                if completed_payload.get(field) in (None, "")
            ]
            if missing:
                raise CompletedActionValidationError(
                    "Missing required fields derived from Strava payload: " + ", ".join(missing)
                )

            item = CompletedAction(**completed_payload)
            session.add(item)
            session.flush()

            normalized_laps = []
            for index, lap in enumerate(activity.get("laps", []) or [], start=1):
                normalized_laps.append(self._build_lap_payload(item.id, lap, index))
            if normalized_laps:
                self.create_laps(session, item.id, normalized_laps)

            session.commit()

            stmt = (
                select(CompletedAction)
                .options(selectinload(CompletedAction.laps))
                .where(CompletedAction.id == item.id)
            )
            return session.execute(stmt).scalar_one(), True

    def get_by_id(self, completed_action_id: str) -> Optional[CompletedAction]:
        with SessionLocal() as session:
            stmt = (
                select(CompletedAction)
                .options(selectinload(CompletedAction.laps))
                .where(CompletedAction.id == self._to_uuid(completed_action_id, "completed_action_id"))
            )
            return session.execute(stmt).scalar_one_or_none()

    def list_all(self) -> List[CompletedAction]:
        with SessionLocal() as session:
            stmt = (
                select(CompletedAction)
                .options(selectinload(CompletedAction.laps))
                .order_by(CompletedAction.created_at.desc())
            )
            return list(session.execute(stmt).scalars().all())

    def update(self, completed_action_id: str, payload: Dict[str, Any]) -> CompletedAction:
        with SessionLocal() as session:
            stmt = (
                select(CompletedAction)
                .options(selectinload(CompletedAction.laps))
                .where(CompletedAction.id == self._to_uuid(completed_action_id, "completed_action_id"))
            )
            item = session.execute(stmt).scalar_one_or_none()
            if item is None:
                raise CompletedActionNotFoundError("completed_action not found")

            data = dict(payload)
            laps_payload = data.pop("laps", None)

            for key, value in data.items():
                setattr(item, key, value)

            if laps_payload is not None:
                item.laps.clear()
                self.create_laps(session, item.id, laps_payload)

            session.commit()

            refresh_stmt = (
                select(CompletedAction)
                .options(selectinload(CompletedAction.laps))
                .where(CompletedAction.id == item.id)
            )
            return session.execute(refresh_stmt).scalar_one()

    def delete(self, completed_action_id: str) -> bool:
        with SessionLocal() as session:
            stmt = select(CompletedAction).where(
                CompletedAction.id == self._to_uuid(completed_action_id, "completed_action_id")
            )
            item = session.execute(stmt).scalar_one_or_none()
            if item is None:
                raise CompletedActionNotFoundError("completed_action not found")

            session.delete(item)
            session.commit()
            return True
