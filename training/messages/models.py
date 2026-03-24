import uuid
from sqlalchemy import Column, String, Text, DateTime, Date, Integer, Float, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from training.db import Base


class Message(Base):
    """
    Message within a chat. Messages are atomic; one row per user or AI turn.
    """

    __tablename__ = "messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_sessions.chatbot_id"), nullable=False)
    sender = Column(Enum("user", "ai", name="message_sender_enum"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(Enum("reflection", "chat", "system", name="message_type_enum"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
