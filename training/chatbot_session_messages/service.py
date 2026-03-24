from __future__ import annotations

from typing import List

from sqlalchemy import select

from training.db import SessionLocal

from .models import ChatbotSessionMessage


class ChatbotSessionMessageService:
    def create(self, payload):
        with SessionLocal() as session:
            item = ChatbotSessionMessage(**payload)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def list_for_session(self, chatbot_id, limit: int = 50) -> List[ChatbotSessionMessage]:
        with SessionLocal() as session:
            stmt = (
                select(ChatbotSessionMessage)
                .where(ChatbotSessionMessage.chatbot_id == chatbot_id)
                .order_by(ChatbotSessionMessage.created_at.asc())
                .limit(limit)
            )
            return list(session.execute(stmt).scalars().all())
