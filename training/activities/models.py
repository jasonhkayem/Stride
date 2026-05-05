import uuid
from sqlalchemy import Column, String, Text, DateTime, Date, Integer, Float, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from training.db import Base


class Activity(Base):
    """
    User workout activity.
    """

    __tablename__ = "activities"

    activity_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    strava_id = Column(String(255), nullable=True)
    activity_type = Column(Enum("run", "bike", "swim", "walk", "hike", "weights", "mobility", "yoga", "other", name="activity_type_enum", create_constraint=True), nullable=False)
    distance = Column(Float, nullable=False)
    duration = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    route_polyline = Column(Text, nullable=True)
    average_heart_rate = Column(Float, nullable=True)
    laps = Column(JSONB, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
