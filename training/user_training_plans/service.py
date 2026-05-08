from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select

from training.common.crud_service import CRUDService
from training.completed_actions.models import CompletedAction
from training.completed_actions.schemas import CompletedActionSchema
from training.training_plan_actions.models import TrainingPlanAction
from training.training_plan_actions.schemas import TrainingPlanActionSchema
from training.training_plan_adjustments.models import TrainingPlanAdjustment
from training.training_plan_adjustments.schemas import TrainingPlanAdjustmentSchema
from training.training_plan_versions.models import TrainingPlanVersion
from training.training_plan_versions.schemas import TrainingPlanVersionSchema
from training.db import SessionLocal

from .models import UserTrainingPlan
from .schemas import UserTrainingPlanSchema


class UserTrainingPlanService(CRUDService):
    def __init__(self):
        super().__init__(UserTrainingPlan, "user_plan_id")

    def create(self, payload: Dict[str, Any]):
        user_id = payload.get("user_id")
        if not user_id:
            raise ValueError("user_id is required")

        with SessionLocal() as session:
            existing = session.execute(
                select(UserTrainingPlan).where(UserTrainingPlan.user_id == self._coerce_pk(user_id))
            ).scalar_one_or_none()
            if existing is not None:
                has_version = session.execute(
                    select(TrainingPlanVersion)
                    .where(TrainingPlanVersion.user_plan_id == existing.user_plan_id)
                    .limit(1)
                ).scalar_one_or_none()
                if has_version is not None:
                    raise ValueError("user already has an active training plan")
                return UserTrainingPlanSchema().dump(existing)

        return super().create(payload)

    def get_with_related(self, user_plan_id: str) -> Optional[Dict[str, Any]]:
        plan = self.get_by_id(user_plan_id)
        if plan is None:
            return None

        with SessionLocal() as session:
            versions = list(
                session.execute(
                    select(TrainingPlanVersion)
                    .where(TrainingPlanVersion.user_plan_id == plan.user_plan_id)
                    .order_by(TrainingPlanVersion.version_number)
                ).scalars().all()
            )
            version_ids = [version.version_id for version in versions]

            actions = list(
                session.execute(
                    select(TrainingPlanAction).where(TrainingPlanAction.version_id.in_(version_ids))
                ).scalars().all()
            ) if version_ids else []
            action_ids = [action.action_id for action in actions]

            completed_actions = list(
                session.execute(
                    select(CompletedAction).where(CompletedAction.training_plan_action_id.in_(action_ids))
                ).scalars().all()
            ) if action_ids else []

            adjustments = list(
                session.execute(
                    select(TrainingPlanAdjustment).where(
                        TrainingPlanAdjustment.user_training_plan_id == plan.user_plan_id
                    )
                ).scalars().all()
            )

            result = UserTrainingPlanSchema().dump(plan)
            result["versions"] = TrainingPlanVersionSchema().dump(versions, many=True)
            result["actions"] = TrainingPlanActionSchema().dump(actions, many=True)
            result["completed_actions"] = CompletedActionSchema().dump(completed_actions, many=True)
            result["adjustments"] = TrainingPlanAdjustmentSchema().dump(adjustments, many=True)
            return result

    def delete(self, record_id: str) -> bool:
        from training.common.crud_service import NotFoundError
        pk = self._coerce_pk(record_id)
        with SessionLocal() as session:
            plan = session.get(UserTrainingPlan, pk)
            if plan is None:
                raise NotFoundError("user training plan not found")
            uid = plan.user_plan_id
            from training.training_plan_versions.service import TrainingPlanVersionService
            TrainingPlanVersionService()._reset_plan_versions(session, uid)
            plan = session.get(UserTrainingPlan, uid)
            session.delete(plan)
            session.commit()
        return True

    def list_all_with_related(self) -> List[Dict[str, Any]]:
        plans = self.list_all()
        results: List[Dict[str, Any]] = []
        for plan in plans:
            enriched = self.get_with_related(str(plan.user_plan_id))
            if enriched is not None:
                results.append(enriched)
        return results
