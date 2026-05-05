import uuid
from sqlalchemy import Column, String, Text, DateTime, Date, Integer, Float, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from training.db import Base


class ChatbotSession(Base):
    """
    Chatbot session for a user.
    """

    __tablename__ = "chatbot_sessions"

    chatbot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    session_type = Column(String, nullable=False)
    related_completed_action_id = Column(UUID(as_uuid=True), ForeignKey("completed_actions.id"), nullable=True)
    related_activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.activity_id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    closed_at = Column(DateTime, nullable=True)
