from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from training.activities.models import Activity
from training.chatbot_session_messages.models import ChatbotSessionMessage
from training.common.crud_service import CRUDService
from training.db import SessionLocal
from training.services.llm_service import LLMService
from training.training_plan_versions.models import TrainingPlanVersion
from training.training_plan_versions.service import TrainingPlanVersionService
from training.user_training_plans.models import UserTrainingPlan

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

    @staticmethod
    def _fmt_pace(sec_per_km: Optional[float]) -> str:
        if not sec_per_km:
            return "--"
        m, s = divmod(int(sec_per_km), 60)
        return f"{m}:{s:02d}/km"

    def _build_user_context(
        self,
        user_id: str,
        related_activity_id: Optional[str] = None,
    ) -> str:
        """Query the DB and build a personalised system-prompt preamble."""
        import uuid as _uuid

        uid = _uuid.UUID(str(user_id))
        lines: List[str] = [
            "You are an expert running coach. Use the athlete's real data below to give "
            "specific, personalised advice. Always reference their actual numbers when relevant. "
            "Format every response using Markdown: use **bold** for key figures and emphasis, "
            "bullet lists (- item) for multiple recommendations, and ## headers when covering "
            "distinct topics. Never write a single wall of plain text. Keep responses under 150 "
            "words unless user asks for detail.\n" 
        ]

        with SessionLocal() as session:
            # --- Focused activity (reflection mode) ---
            if related_activity_id:
                act = session.execute(
                    select(Activity).where(
                        Activity.activity_id == _uuid.UUID(str(related_activity_id))
                    )
                ).scalar_one_or_none()
                if act:
                    duration_min = act.duration // 60
                    pace = self._fmt_pace(act.duration / act.distance if act.distance else None)
                    lines.append(
                        f"ACTIVITY BEING REFLECTED ON:\n"
                        f"  Type: {act.activity_type}, Date: {act.timestamp.date()}, "
                        f"  Distance: {act.distance:.2f} km, Duration: {duration_min} min, "
                        f"  Avg pace: {pace}\n"
                    )

            # --- Last 5 activities ---
            recent = list(
                session.execute(
                    select(Activity)
                    .where(Activity.user_id == uid)
                    .order_by(Activity.timestamp.desc())
                    .limit(5)
                ).scalars().all()
            )
            if recent:
                lines.append("RECENT ACTIVITIES (newest first):")
                for act in recent:
                    pace = self._fmt_pace(act.duration / act.distance if act.distance else None)
                    lines.append(
                        f"  - {act.timestamp.date()} | {act.activity_type} | "
                        f"{act.distance:.2f} km | {act.duration // 60} min | {pace}"
                    )
                lines.append("")

            # --- Current training plan ---
            plan = session.execute(
                select(UserTrainingPlan).where(UserTrainingPlan.user_id == uid)
            ).scalar_one_or_none()
            if plan and plan.current_version_id:
                version = session.get(TrainingPlanVersion, plan.current_version_id)
                if version and version.plan_snapshot:
                    snap = version.plan_snapshot
                    lines.append("CURRENT TRAINING PLAN:")
                    if snap.get("goal_race"):
                        lines.append(f"  Goal race: {snap['goal_race']}")
                    if snap.get("goal_time"):
                        lines.append(f"  Goal time: {snap['goal_time']}")
                    if snap.get("duration_weeks"):
                        lines.append(f"  Plan length: {snap['duration_weeks']} weeks")
                    pace_targets = snap.get("pace_targets", {})
                    if pace_targets:
                        easy = pace_targets.get("easy", {})
                        tempo = pace_targets.get("tempo", {})
                        lines.append(
                            f"  Easy pace: {easy.get('min','--')}–{easy.get('max','--')}"
                        )
                        lines.append(
                            f"  Tempo pace: {tempo.get('min','--')}–{tempo.get('max','--')}"
                        )
                    lines.append("")

        return "\n".join(lines)

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

            # Build a data-aware system prompt from the user's actual records
            system_prompt = self._build_user_context(
                user_id=str(chat.user_id),
                related_activity_id=(
                    str(chat.related_activity_id) if chat.related_activity_id else None
                ),
            )

            llm_messages = self._build_llm_messages(history=history, system_prompt=system_prompt)
            ai_text = self.llm_service.chat_completion(llm_messages, max_tokens=600)

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
