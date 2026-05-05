import uuid
from sqlalchemy import Column, String, Text, DateTime, Date, Integer, Float, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from training.db import Base


class User(Base):
    """
    Platform user account.
    """

    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    platform_role = Column(Enum("user", "super_admin", name="platform_role_enum"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    username = Column(String(255), unique=True, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    profile_picture_url = Column(String(255), nullable=True)
    strava_athlete_id = Column(String(64), unique=True, nullable=True)
    strava_connected_at = Column(DateTime, nullable=True)
    weekly_goal_km = Column(Float, nullable=True)
