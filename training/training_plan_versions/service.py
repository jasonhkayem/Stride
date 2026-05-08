from __future__ import annotations

from copy import deepcopy
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import re

from sqlalchemy import func, select, delete as sa_delete

from training.common.crud_service import CRUDService
from training.db import SessionLocal
from training.training_plan_actions.models import TrainingPlanAction
from training.training_plan_actions.schemas import TrainingPlanActionSchema
from training.completed_actions.models import CompletedAction
from training.completed_actions.schemas import CompletedActionSchema
from training.completed_action_laps.models import CompletedActionLap
from training.training_plan_adjustments.models import TrainingPlanAdjustment
from training.training_plan_adjustments.schemas import TrainingPlanAdjustmentSchema
from training.user_training_plans.models import UserTrainingPlan
from training.services.llm_service import LLMService, LLMServiceError
from training.training_plan_templates.models import TrainingPlanTemplate

from .models import TrainingPlanVersion
from .schemas import TrainingPlanVersionSchema


class TrainingPlanVersionService(CRUDService):
    def __init__(self):
        super().__init__(TrainingPlanVersion, "version_id")
        self.llm = LLMService()

    def create(self, payload: Dict[str, Any]):
        user_plan_id = payload.get("user_plan_id")
        if not user_plan_id:
            raise ValueError("user_plan_id is required")

        with SessionLocal() as session:
            uid = self._coerce_pk(user_plan_id)
            plan = session.get(UserTrainingPlan, uid)
            if plan is None:
                raise ValueError("user training plan not found")

            data = dict(payload)
            data["user_plan_id"] = uid

            if data.get("version_number") is None:
                max_version_stmt = select(func.max(TrainingPlanVersion.version_number)).where(
                    TrainingPlanVersion.user_plan_id == uid
                )
                max_version = session.execute(max_version_stmt).scalar() or 0
                data["version_number"] = int(max_version) + 1

            item = TrainingPlanVersion(**data)
            session.add(item)
            session.flush()

            # Latest created version becomes the current version for this plan.
            plan.current_version_id = item.version_id

            session.commit()
            session.refresh(item)
            return item

    def get_with_related(self, version_id: str) -> Optional[Dict[str, Any]]:
        version = self.get_by_id(version_id)
        if version is None:
            return None

        with SessionLocal() as session:
            actions = list(
                session.execute(
                    select(TrainingPlanAction).where(TrainingPlanAction.version_id == version.version_id)
                ).scalars().all()
            )
            action_ids = [action.action_id for action in actions]

            completed_actions = list(
                session.execute(
                    select(CompletedAction).where(CompletedAction.training_plan_action_id.in_(action_ids))
                ).scalars().all()
            ) if action_ids else []

            adjustments = list(
                session.execute(
                    select(TrainingPlanAdjustment).where(
                        (TrainingPlanAdjustment.previous_version_id == version.version_id)
                        | (TrainingPlanAdjustment.new_version_id == version.version_id)
                    )
                ).scalars().all()
            )

            result = TrainingPlanVersionSchema().dump(version)
            result["actions"] = TrainingPlanActionSchema().dump(actions, many=True)
            result["completed_actions"] = CompletedActionSchema().dump(completed_actions, many=True)
            result["adjustments"] = TrainingPlanAdjustmentSchema().dump(adjustments, many=True)
            return result

    def list_all_with_related(self) -> List[Dict[str, Any]]:
        versions = self.list_all()
        results: List[Dict[str, Any]] = []
        for version in versions:
            enriched = self.get_with_related(str(version.version_id))
            if enriched is not None:
                results.append(enriched)
        return results

    def validate_ai_actions(self, payload: Dict[str, Any]) -> None:
        proposed_actions = payload.get("proposed_actions", [])
        rationale = payload.get("rationale", "")

        if not isinstance(proposed_actions, list):
            raise ValueError("proposed_actions must be a list")
        if not isinstance(rationale, str) or len(rationale.strip()) < 10:
            raise ValueError("rationale must be at least 10 characters")

        valid_actions = {"adjust_volume", "adjust_intensity", "insert_rest_day", "reschedule_session"}
        valid_scopes = {"next_week", "current_week"}

        def _is_date(value: Any) -> bool:
            if not isinstance(value, str):
                return False
            try:
                datetime.date.fromisoformat(value)
                return True
            except ValueError:
                return False

        for index, action in enumerate(proposed_actions, start=1):
            if not isinstance(action, dict):
                raise ValueError(f"proposed_actions[{index}] must be an object")
            action_type = action.get("action")
            if action_type not in valid_actions:
                raise ValueError(f"proposed_actions[{index}].action is invalid")

            if "percentage" in action:
                percentage = action.get("percentage")
                if not isinstance(percentage, int) or not (-20 <= percentage <= 10):
                    raise ValueError(f"proposed_actions[{index}].percentage out of range")

            if "intensity_adjustment" in action:
                intensity = action.get("intensity_adjustment")
                if not isinstance(intensity, (int, float)) or not (-15 <= intensity <= 10):
                    raise ValueError(f"proposed_actions[{index}].intensity_adjustment out of range")

            if "scope" in action and action.get("scope") not in valid_scopes:
                raise ValueError(f"proposed_actions[{index}].scope is invalid")

            if action_type == "insert_rest_day":
                if not _is_date(action.get("date")):
                    raise ValueError(f"proposed_actions[{index}].date must be YYYY-MM-DD")

            if action_type == "reschedule_session":
                if not _is_date(action.get("from_date")) or not _is_date(action.get("to_date")):
                    raise ValueError(f"proposed_actions[{index}].from_date/to_date must be YYYY-MM-DD")

    def apply_ai_actions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        version_id = payload.get("version_id")
        if not version_id:
            raise ValueError("version_id is required")

        self.validate_ai_actions(payload)

        with SessionLocal() as session:
            current_version = session.get(TrainingPlanVersion, self._coerce_pk(version_id))
            if current_version is None:
                raise ValueError("version not found")

            max_version_stmt = select(func.max(TrainingPlanVersion.version_number)).where(
                TrainingPlanVersion.user_plan_id == current_version.user_plan_id
            )
            max_version = session.execute(max_version_stmt).scalar() or 0

            next_snapshot = deepcopy(current_version.plan_snapshot or {})
            next_snapshot["ai_actions"] = payload.get("proposed_actions", [])
            next_snapshot["ai_rationale"] = payload.get("rationale")

            new_version = TrainingPlanVersion(
                user_plan_id=current_version.user_plan_id,
                version_number=int(max_version) + 1,
                plan_snapshot=next_snapshot,
                created_by="ai",
                change_summary=payload.get("rationale"),
            )
            session.add(new_version)
            session.flush()

            created_actions: List[TrainingPlanAction] = []
            for action in payload.get("proposed_actions", []):
                action_row = TrainingPlanAction(
                    version_id=new_version.version_id,
                    action_type=action.get("action"),
                    parameters={key: value for key, value in action.items() if key != "action"},
                )
                session.add(action_row)
                created_actions.append(action_row)

            user_plan = session.get(UserTrainingPlan, current_version.user_plan_id)
            if user_plan is not None:
                user_plan.current_version_id = new_version.version_id

            session.commit()
            session.refresh(new_version)
            for action in created_actions:
                session.refresh(action)

            return {
                "new_version": TrainingPlanVersionSchema().dump(new_version),
                "actions": TrainingPlanActionSchema().dump(created_actions, many=True),
            }

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                raise ValueError("LLM response did not contain JSON")
            return json.loads(match.group(0))

    def generate_plan_version(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        user_plan_id = payload.get("user_plan_id")
        if not user_plan_id:
            raise ValueError("user_plan_id is required")

        with SessionLocal() as session:
            uid = self._coerce_pk(user_plan_id)
            plan = session.get(UserTrainingPlan, uid)
            if plan is None:
                raise ValueError("user training plan not found")

            max_version_stmt = select(func.max(TrainingPlanVersion.version_number)).where(
                TrainingPlanVersion.user_plan_id == uid
            )
            next_version = int(session.execute(max_version_stmt).scalar() or 0) + 1

            system_prompt = (
                "You are a coaching engine. Return ONLY valid JSON with keys: "
                "plan_overview (string), weeks (array). "
                "Each week item: {\"week\": int, \"sessions\": ["
                "{\"day\": string, \"type\": string, \"duration_min\": int, "
                "\"distance_km\": number, \"notes\": string}]}. "
                "No extra keys, no markdown."
            )
            user_prompt = json.dumps(payload, ensure_ascii=False)

            try:
                content = self.llm.chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    max_tokens=800,
                )
            except LLMServiceError as exc:
                raise ValueError(str(exc)) from exc

            plan_snapshot = self._extract_json(content)

            version = TrainingPlanVersion(
                user_plan_id=uid,
                version_number=next_version,
                plan_snapshot=plan_snapshot,
                created_by="ai",
                change_summary="AI-generated training plan",
            )
            session.add(version)
            session.flush()
            plan.current_version_id = version.version_id
            session.commit()
            session.refresh(version)

            return {"version": TrainingPlanVersionSchema().dump(version), "plan_snapshot": plan_snapshot}

    @staticmethod
    def _parse_goal_time_to_seconds(goal_time: str) -> int:
        value = (goal_time or "").strip()
        if not value:
            raise ValueError("goal_time is required")
        parts = value.split(":")
        if len(parts) == 2:
            minutes, seconds = parts
            hours = 0
        elif len(parts) == 3:
            hours, minutes, seconds = parts
        else:
            raise ValueError("goal_time must be MM:SS or HH:MM:SS")
        try:
            h = int(hours)
            m = int(minutes)
            s = int(seconds)
        except ValueError as exc:
            raise ValueError("goal_time must be numeric") from exc
        if h < 0 or m < 0 or s < 0:
            raise ValueError("goal_time must be positive")
        return h * 3600 + m * 60 + s

    @staticmethod
    def _race_distance_km(goal_race: str) -> float:
        mapping = {
            "5k": 5.0,
            "10k": 10.0,
            "half_marathon": 21.0975,
            "marathon": 42.195,
        }
        distance = mapping.get(str(goal_race).strip().lower())
        if distance is None:
            raise ValueError("unsupported goal_race for template plan")
        return distance

    @staticmethod
    def _compute_runs_per_week(base_pace_sec_per_km: int, template_min: int) -> int:
        """Bump weekly session count based on goal pace — faster targets need more volume."""
        if base_pace_sec_per_km <= 240:    # ≤ 4:00/km — elite
            return max(template_min, 6)
        if base_pace_sec_per_km <= 270:    # ≤ 4:30/km — competitive
            return max(template_min, 5)
        if base_pace_sec_per_km <= 330:    # ≤ 5:30/km — intermediate
            return max(template_min, 4)
        if base_pace_sec_per_km <= 390:    # ≤ 6:30/km — recreational
            return max(template_min, 3)
        return template_min

    @staticmethod
    def _pace_range(base_sec_per_km: int, slow: int, fast: int) -> Dict[str, str]:
        def fmt(sec: int) -> str:
            minutes = sec // 60
            seconds = sec % 60
            return f"{minutes}:{seconds:02d}/km"

        return {
            "min": fmt(base_sec_per_km + slow),
            "max": fmt(base_sec_per_km + fast),
        }

    def _generate_weekly_sessions(
        self,
        goal_race: str,
        duration_weeks: int,
        min_runs_per_week: int,
        pace_targets: Dict[str, Any],
        goal_time: str,
    ) -> Dict[str, Any]:
        """Call the LLM to produce a week-by-week schedule."""

        def _fmt(p: Dict) -> str:
            return f"{p.get('min','--')}–{p.get('max','--')}"

        system_prompt = (
            "You are an expert running coach. Generate a structured training plan. "
            "Return ONLY valid JSON — no markdown, no extra keys — with this exact shape: "
            '{"plan_overview": "string", "weeks": [{"week": 1, "phase": "string", '
            '"sessions": [{"day": "Monday", "type": "easy_run|tempo|long_run|interval|rest|cross_train|race", '
            '"distance_km": 5.0, "duration_min": 30, "notes": "string"}]}]}. '
            "Only include days that have a session (skip rest days or mark them type=rest with distance_km=0). "
            "The final week must include a race day session with type=race, day='Race Day', and the full race distance and estimated finish time as notes. "
            "For interval sessions, notes MUST follow this format exactly: "
            "'Xkm warmup, NxYm @ P/km, Xkm cooldown' — e.g. '1.5km warmup, 8x400m @ 4:10/km, 1.5km cooldown'. "
            "For all other session types, keep notes under 10 words."
        )

        user_prompt = (
            f"Create a {duration_weeks}-week {goal_race.replace('_', ' ')} training plan. "
            f"Goal time: {goal_time}. "
            f"Runs per week: {min_runs_per_week}. "
            f"Pace targets — easy: {_fmt(pace_targets['easy'])}, "
            f"tempo: {_fmt(pace_targets['tempo'])}, "
            f"long run: {_fmt(pace_targets['long'])}, "
            f"intervals: {_fmt(pace_targets['interval'])}, "
            f"race pace: {_fmt(pace_targets['race_pace'])}. "
            f"Structure the plan with base, build, peak, and taper phases across the {duration_weeks} weeks."
        )

        try:
            content = self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
                max_tokens=3000,
            )
        except LLMServiceError as exc:
            raise ValueError(str(exc)) from exc

        return self._extract_json(content)

    def _reset_plan_versions(self, session, uid) -> None:
        """Delete all versions (and related rows) for a user plan, reset current_version_id."""
        existing_versions = list(
            session.execute(
                select(TrainingPlanVersion).where(TrainingPlanVersion.user_plan_id == uid)
            ).scalars().all()
        )
        version_ids = [v.version_id for v in existing_versions]
        if not version_ids:
            return

        action_ids = list(
            session.execute(
                select(TrainingPlanAction.action_id).where(TrainingPlanAction.version_id.in_(version_ids))
            ).scalars().all()
        )
        if action_ids:
            session.execute(sa_delete(CompletedActionLap).where(
                CompletedActionLap.completed_action_id.in_(
                    select(CompletedAction.id).where(CompletedAction.training_plan_action_id.in_(action_ids))
                )
            ))
            session.execute(sa_delete(CompletedAction).where(
                CompletedAction.training_plan_action_id.in_(action_ids)
            ))
        session.execute(sa_delete(TrainingPlanAdjustment).where(
            TrainingPlanAdjustment.user_training_plan_id == uid
        ))
        session.execute(sa_delete(TrainingPlanAction).where(
            TrainingPlanAction.version_id.in_(version_ids)
        ))
        plan = session.get(UserTrainingPlan, uid)
        if plan:
            plan.current_version_id = None
        session.flush()
        session.execute(sa_delete(TrainingPlanVersion).where(
            TrainingPlanVersion.user_plan_id == uid
        ))
        session.flush()

    def generate_from_template(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        user_plan_id = payload.get("user_plan_id")
        template_id = payload.get("template_id")
        goal_time = payload.get("goal_time")
        reset = bool(payload.get("reset", False))
        if not user_plan_id:
            raise ValueError("user_plan_id is required")
        if not template_id:
            raise ValueError("template_id is required")

        with SessionLocal() as session:
            uid = self._coerce_pk(user_plan_id)
            plan = session.get(UserTrainingPlan, uid)
            if plan is None:
                raise ValueError("user training plan not found")

            tpl = session.get(TrainingPlanTemplate, self._coerce_pk(template_id))
            if tpl is None:
                raise ValueError("training plan template not found")

            total_seconds = self._parse_goal_time_to_seconds(str(goal_time))
            distance_km = self._race_distance_km(tpl.goal_race)
            base_pace = int(round(total_seconds / distance_km))

            pace_targets = {
                "race_pace": self._pace_range(base_pace, 0, 0),
                "easy": self._pace_range(base_pace, 45, 75),
                "long": self._pace_range(base_pace, 30, 60),
                "tempo": self._pace_range(base_pace, 10, 20),
                "interval": self._pace_range(base_pace, -15, -5),
            }

            template_min = (tpl.structure or {}).get("min_runs_per_week", 3)
            min_runs = self._compute_runs_per_week(base_pace, template_min)

            llm_plan = self._generate_weekly_sessions(
                goal_race=tpl.goal_race,
                duration_weeks=tpl.duration_weeks,
                min_runs_per_week=min_runs,
                pace_targets=pace_targets,
                goal_time=str(goal_time),
            )

            if reset:
                self._reset_plan_versions(session, uid)
                plan = session.get(UserTrainingPlan, uid)
                plan.template_id = tpl.template_id
                next_version = 1
            else:
                max_version_stmt = select(func.max(TrainingPlanVersion.version_number)).where(
                    TrainingPlanVersion.user_plan_id == uid
                )
                next_version = int(session.execute(max_version_stmt).scalar() or 0) + 1

            plan_snapshot = {
                "source": "template",
                "template_id": str(tpl.template_id),
                "goal_race": tpl.goal_race,
                "duration_weeks": tpl.duration_weeks,
                "min_runs_per_week": min_runs,
                "goal_time": str(goal_time),
                "pace_targets": pace_targets,
                "plan_overview": llm_plan.get("plan_overview", ""),
                "weeks": llm_plan.get("weeks", []),
            }

            version = TrainingPlanVersion(
                user_plan_id=uid,
                version_number=next_version,
                plan_snapshot=plan_snapshot,
                created_by="ai",
                change_summary=f"AI-generated {tpl.goal_race} plan — goal {goal_time}",
            )
            session.add(version)
            session.flush()
            plan.current_version_id = version.version_id
            session.commit()
            session.refresh(version)

            return {"version": TrainingPlanVersionSchema().dump(version), "plan_snapshot": plan_snapshot}
