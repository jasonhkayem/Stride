import uuid
from sqlalchemy import Column, String, Text, DateTime, Date, Integer, Float, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from training.db import Base


class TrainingPlanTemplate(Base):
    """
    Template for training plans.
    """

    __tablename__ = "training_plan_templates"

    template_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_race = Column(String(255), nullable=False)
    duration_weeks = Column(Integer, nullable=False)
    structure = Column(JSONB, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
