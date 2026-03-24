from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import desc, select

from training.db import SessionLocal


class NotFoundError(Exception):
    """Raised when a record is not found."""


class CRUDService:
    """Generic SQLAlchemy CRUD service."""

    def __init__(self, model, pk_field: str):
        self.model = model
        self.pk_field = pk_field

    def _coerce_pk(self, value: Any) -> Any:
        column = self.model.__table__.columns[self.pk_field]
        try:
            python_type = column.type.python_type
        except (AttributeError, NotImplementedError):
            python_type = None

        if python_type is uuid.UUID:
            return uuid.UUID(str(value))
        if python_type is int:
            return int(value)
        return value

    def create(self, payload: Dict[str, Any]):
        with SessionLocal() as session:
            item = self.model(**payload)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def get_by_id(self, record_id: Any):
        with SessionLocal() as session:
            stmt = select(self.model).where(
                getattr(self.model, self.pk_field) == self._coerce_pk(record_id)
            )
            return session.execute(stmt).scalar_one_or_none()

    def list_all(self) -> List[Any]:
        with SessionLocal() as session:
            if "created_at" in self.model.__table__.columns:
                stmt = select(self.model).order_by(desc(getattr(self.model, "created_at")))
            else:
                stmt = select(self.model)
            return list(session.execute(stmt).scalars().all())

    def update(self, record_id: Any, payload: Dict[str, Any]):
        with SessionLocal() as session:
            stmt = select(self.model).where(
                getattr(self.model, self.pk_field) == self._coerce_pk(record_id)
            )
            item = session.execute(stmt).scalar_one_or_none()
            if item is None:
                raise NotFoundError(f"{self.model.__tablename__} record not found")

            for key, value in payload.items():
                setattr(item, key, value)

            session.commit()
            session.refresh(item)
            return item

    def delete(self, record_id: Any) -> bool:
        with SessionLocal() as session:
            stmt = select(self.model).where(
                getattr(self.model, self.pk_field) == self._coerce_pk(record_id)
            )
            item = session.execute(stmt).scalar_one_or_none()
            if item is None:
                raise NotFoundError(f"{self.model.__tablename__} record not found")

            session.delete(item)
            session.commit()
            return True