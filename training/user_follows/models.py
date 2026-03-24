import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID

from training.db import Base


class UserFollow(Base):
    """
    Follow relationship between users.
    """

    __tablename__ = "user_follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_user_follows_pair"),
        CheckConstraint("follower_id <> following_id", name="ck_user_follows_no_self_follow"),
    )

    follow_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    following_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
