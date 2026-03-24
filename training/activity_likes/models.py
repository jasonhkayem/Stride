import uuid
from sqlalchemy import Column, String, Text, DateTime, Date, Integer, Float, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from training.db import Base


class ActivityLike(Base):
    """
    Like on an activity.
    """

    __tablename__ = "activity_likes"

    like_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.activity_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
