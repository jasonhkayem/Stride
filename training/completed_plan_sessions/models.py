from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from training.db import Base


class CompletedPlanSession(Base):
    __tablename__ = "completed_plan_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    version_id = Column(UUID(as_uuid=True), ForeignKey("training_plan_versions.version_id", ondelete="CASCADE"), nullable=False)
    week_index = Column(Integer, nullable=False)
    session_index = Column(Integer, nullable=False)
    completed_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "version_id", "week_index", "session_index", name="uq_completed_plan_session"),
    )
