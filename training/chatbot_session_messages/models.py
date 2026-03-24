import uuid
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID

from training.db import Base


class ChatbotSessionMessage(Base):
    """
    Message in a chatbot session.
    """

    __tablename__ = "chatbot_session_messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chatbot_id = Column(UUID(as_uuid=True), ForeignKey("chatbot_sessions.chatbot_id"), nullable=False)
    sender = Column(
        Enum("user", "assistant", "system", name="chatbot_session_sender_enum"),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
