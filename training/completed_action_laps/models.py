import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from training.db import Base


class CompletedActionLap(Base):
    """
    Per-lap split metrics for a completed action.
    """

    __tablename__ = "completed_action_laps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    completed_action_id = Column(UUID(as_uuid=True), ForeignKey("completed_actions.id"), nullable=False)
    lap_index = Column(Integer, nullable=False)
    distance_km = Column(Numeric(5, 2), nullable=False)
    moving_time_min = Column(Numeric(5, 2), nullable=False)
    avg_pace_sec_per_km = Column(Integer, nullable=False)
    avg_heart_rate = Column(Integer, nullable=True)
    elevation_gain_m = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    completed_action = relationship("CompletedAction", back_populates="laps")
