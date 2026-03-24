import uuid
from sqlalchemy import Column, String, Text, DateTime, Date, Integer, Float, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from training.db import Base


class TrainingPlanVersion(Base):
    """
    Immutable snapshot of a training plan after a modification.
    """

    __tablename__ = "training_plan_versions"

    version_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_plan_id = Column(UUID(as_uuid=True), ForeignKey("user_training_plans.user_plan_id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    plan_snapshot = Column(JSONB, nullable=False)
    created_by = Column(Enum("ai", "system", name="plan_version_created_by_enum"), nullable=False)
    change_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
