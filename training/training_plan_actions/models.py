import uuid
from sqlalchemy import Column, String, Text, DateTime, Date, Integer, Float, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from training.db import Base


class TrainingPlanAction(Base):
    """
    AI or system action applied to a training plan version.
    """

    __tablename__ = "training_plan_actions"

    action_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id = Column(UUID(as_uuid=True), ForeignKey("training_plan_versions.version_id"), nullable=False)
    action_type = Column(String(100), nullable=False)
    parameters = Column(JSONB, nullable=False)
    applied_at = Column(DateTime, server_default=func.now(), nullable=False)
