import uuid

from sqlalchemy import BIGINT, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from training.db import Base


class CompletedAction(Base):
    """
    Persisted completion data for planned actions.
    """

    __tablename__ = "completed_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    training_plan_action_id = Column(UUID(as_uuid=True), ForeignKey("training_plan_actions.action_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    strava_activity_id = Column(BIGINT, nullable=True)
    name = Column(String(255), nullable=False)
    action_type = Column(String(30), nullable=False)
    actual_distance_km = Column(Numeric(5, 2), nullable=False)
    actual_duration_min = Column(Integer, nullable=False)
    avg_pace_sec_per_km = Column(Integer, nullable=False)
    avg_heart_rate = Column(Integer, nullable=True)
    elevation_gain_m = Column(Integer, nullable=True)
    calories = Column(Numeric(6, 2), nullable=True)
    gear_id = Column(String(50), nullable=True)
    manual_entry = Column(Boolean, nullable=False, default=False, server_default="false")
    completed_at = Column(DateTime(timezone=True), nullable=False)
    route_polyline = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    training_plan_action = relationship("TrainingPlanAction", foreign_keys=[training_plan_action_id])
    user = relationship("User", foreign_keys=[user_id])
    laps = relationship(
        "CompletedActionLap",
        back_populates="completed_action",
        cascade="all, delete-orphan",
        order_by="CompletedActionLap.lap_index",
    )
