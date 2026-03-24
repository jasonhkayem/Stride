from __future__ import annotations

import json
from typing import Any, Dict, List

from sqlalchemy import select

from training.chatbot_session_messages.models import ChatbotSessionMessage
from training.common.crud_service import CRUDService
from training.db import SessionLocal
from training.services.llm_service import LLMService
from training.training_plan_versions.service import TrainingPlanVersionService

from .models import ChatbotSession


class ChatbotSessionService(CRUDService):
    def __init__(self):
        super().__init__(ChatbotSession, "chatbot_id")
        self.llm_service = LLMService()
        self.training_plan_version_service = TrainingPlanVersionService()

    def list_messages(self, chatbot_id: str, limit: int = 50) -> List[ChatbotSessionMessage]:
        with SessionLocal() as session:
            stmt = (
                select(ChatbotSessionMessage)
                .where(ChatbotSessionMessage.chatbot_id == self._coerce_pk(chatbot_id))
                .order_by(ChatbotSessionMessage.created_at.asc())
                .limit(limit)
            )
            return list(session.execute(stmt).scalars().all())

    def _build_llm_messages(
        self,
        history: List[ChatbotSessionMessage],
        system_prompt: str,
    ) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": system_prompt}]
        role_map = {"user": "user", "assistant": "assistant", "system": "system"}
        for item in history:
            role = role_map.get(item.sender, "user")
            messages.append({"role": role, "content": item.content})
        return messages

    def generate_reply(
        self,
        chatbot_id: str,
        user_message: str,
        system_prompt: str = "You are a helpful running coach assistant.",
        max_context_messages: int = 20,
    ) -> Dict[str, Any]:
        if not user_message or not user_message.strip():
            raise ValueError("user_message is required")

        with SessionLocal() as session:
            chat = session.execute(
                select(ChatbotSession).where(ChatbotSession.chatbot_id == self._coerce_pk(chatbot_id))
            ).scalar_one_or_none()
            if chat is None:
                raise ValueError("chatbot session not found")

            user_msg = ChatbotSessionMessage(
                chatbot_id=chat.chatbot_id,
                sender="user",
                content=user_message.strip(),
            )
            session.add(user_msg)
            session.flush()

            history_stmt = (
                select(ChatbotSessionMessage)
                .where(ChatbotSessionMessage.chatbot_id == chat.chatbot_id)
                .order_by(ChatbotSessionMessage.created_at.desc())
                .limit(max_context_messages)
            )
            history = list(session.execute(history_stmt).scalars().all())
            history.reverse()

            llm_messages = self._build_llm_messages(history=history, system_prompt=system_prompt)
            ai_text = self.llm_service.chat_completion(llm_messages)

            ai_msg = ChatbotSessionMessage(
                chatbot_id=chat.chatbot_id,
                sender="assistant",
                content=ai_text,
            )
            session.add(ai_msg)
            session.commit()
            session.refresh(ai_msg)

            return {
                "chatbot_id": str(chat.chatbot_id),
                "user_message": user_msg.content,
                "assistant_message": ai_msg.content,
                "assistant_message_id": str(ai_msg.message_id),
                "created_at": ai_msg.created_at,
            }

    @staticmethod
    def _extract_json_object(text: str) -> Dict[str, Any]:
        raw = (text or "").strip()
        if not raw:
            raise ValueError("LLM returned empty response")

        if raw.startswith("```"):
            lines = raw.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            raw = "\n".join(lines).strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError("LLM response is not valid JSON")
            return json.loads(raw[start : end + 1])

    def suggest_training_plan_actions(
        self,
        chatbot_id: str,
        version_id: str,
        user_prompt: str,
        apply_actions: bool = False,
    ) -> Dict[str, Any]:
        if not user_prompt or not user_prompt.strip():
            raise ValueError("user_prompt is required")

        with SessionLocal() as session:
            chat = session.execute(
                select(ChatbotSession).where(ChatbotSession.chatbot_id == self._coerce_pk(chatbot_id))
            ).scalar_one_or_none()
            if chat is None:
                raise ValueError("chatbot session not found")

            user_msg = ChatbotSessionMessage(
                chatbot_id=chat.chatbot_id,
                sender="user",
                content=user_prompt.strip(),
            )
            session.add(user_msg)
            session.flush()

            schema_instruction = (
                "You are a running coach assistant. "
                "Return ONLY valid JSON with this exact top-level shape: "
                '{"proposed_actions":[{"action":"adjust_volume|adjust_intensity|insert_rest_day|reschedule_session",'
                '"percentage":-20..10,"intensity_adjustment":-15..10,"date":"YYYY-MM-DD","from_date":"YYYY-MM-DD",'
                '"to_date":"YYYY-MM-DD","scope":"next_week|current_week"}],"rationale":"string >= 10 chars"}. '
                "Do not include markdown or extra keys."
            )

            llm_messages = [
                {"role": "system", "content": schema_instruction},
                {"role": "user", "content": user_prompt.strip()},
            ]
            ai_text = self.llm_service.chat_completion(llm_messages)

            ai_msg = ChatbotSessionMessage(
                chatbot_id=chat.chatbot_id,
                sender="assistant",
                content=ai_text,
            )
            session.add(ai_msg)
            session.commit()

        suggestion_payload = self._extract_json_object(ai_text)
        suggestion_payload["version_id"] = version_id
        self.training_plan_version_service.validate_ai_actions(suggestion_payload)

        result: Dict[str, Any] = {
            "chatbot_id": str(chatbot_id),
            "version_id": str(version_id),
            "validated_suggestion": {
                "proposed_actions": suggestion_payload.get("proposed_actions", []),
                "rationale": suggestion_payload.get("rationale", ""),
            },
            "applied": False,
        }

        if apply_actions:
            apply_result = self.training_plan_version_service.apply_ai_actions(suggestion_payload)
            result["applied"] = True
            result["apply_result"] = apply_result

        return result
