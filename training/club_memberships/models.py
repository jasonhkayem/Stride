import uuid
from sqlalchemy import Column, String, Text, DateTime, Date, Integer, Float, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from training.db import Base


class ClubMembership(Base):
    """
    User membership in a club.
    """

    __tablename__ = "club_memberships"

    membership_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(UUID(as_uuid=True), ForeignKey("clubs.club_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    role = Column(Enum("member", "club_admin", name="club_membership_role_enum"), nullable=False)
    status = Column(Enum("pending", "approved", "rejected", name="club_membership_status_enum"), nullable=False)
    joined_at = Column(DateTime, nullable=True)
