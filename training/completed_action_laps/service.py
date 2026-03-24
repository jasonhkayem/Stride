from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select

from training.db import SessionLocal

from .models import CompletedActionLap


class CompletedActionLapNotFoundError(Exception):
    """Raised when lap record is not found."""


class CompletedActionLapValidationError(Exception):
    """Raised when lap payload is invalid."""


class CompletedActionLapService:
    """CRUD service for completed action laps."""

    @staticmethod
    def _to_uuid(value: str, field_name: str) -> uuid.UUID:
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError) as exc:
            raise CompletedActionLapValidationError(f"{field_name} must be a valid UUID") from exc

    def create(self, payload: Dict[str, Any]) -> CompletedActionLap:
        with SessionLocal() as session:
            item = CompletedActionLap(**payload)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def bulk_create(self, completed_action_id: str, laps_payload: List[Dict[str, Any]]) -> List[CompletedActionLap]:
        completed_action_uuid = self._to_uuid(completed_action_id, "completed_action_id")
        with SessionLocal() as session:
            created: List[CompletedActionLap] = []
            for index, lap in enumerate(laps_payload, start=1):
                data = dict(lap)
                data["completed_action_id"] = completed_action_uuid
                data.setdefault("lap_index", index)
                item = CompletedActionLap(**data)
                session.add(item)
                created.append(item)

            session.commit()
            for item in created:
                session.refresh(item)
            return created

    def get_by_id(self, lap_id: str) -> Optional[CompletedActionLap]:
        with SessionLocal() as session:
            stmt = select(CompletedActionLap).where(
                CompletedActionLap.id == self._to_uuid(lap_id, "lap_id")
            )
            return session.execute(stmt).scalar_one_or_none()

    def list_all(self) -> List[CompletedActionLap]:
        with SessionLocal() as session:
            stmt = select(CompletedActionLap).order_by(CompletedActionLap.created_at.desc())
            return list(session.execute(stmt).scalars().all())

    def update(self, lap_id: str, payload: Dict[str, Any]) -> CompletedActionLap:
        with SessionLocal() as session:
            stmt = select(CompletedActionLap).where(
                CompletedActionLap.id == self._to_uuid(lap_id, "lap_id")
            )
            item = session.execute(stmt).scalar_one_or_none()
            if item is None:
                raise CompletedActionLapNotFoundError("completed_action_lap not found")

            for key, value in payload.items():
                setattr(item, key, value)

            session.commit()
            session.refresh(item)
            return item

    def delete(self, lap_id: str) -> bool:
        with SessionLocal() as session:
            stmt = select(CompletedActionLap).where(
                CompletedActionLap.id == self._to_uuid(lap_id, "lap_id")
            )
            item = session.execute(stmt).scalar_one_or_none()
            if item is None:
                raise CompletedActionLapNotFoundError("completed_action_lap not found")

            session.delete(item)
            session.commit()
            return True
