from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json

from training.common.crud_service import CRUDService

from .models import TrainingPlanAction


class TrainingPlanActionService(CRUDService):
    def __init__(self):
        super().__init__(TrainingPlanAction, "action_id")

    def validate_ai_actions(self, payload: Dict[str, Any]) -> None:
        try:
            import jsonschema
        except ImportError as exc:
            raise RuntimeError("jsonschema is required for AI action validation") from exc

        schema_path = Path(__file__).resolve().parents[2] / "ai" / "schemas" / "ai_action_schema.json"
        with schema_path.open("r", encoding="utf-8") as handle:
            ai_schema = json.load(handle)

        jsonschema.validate(
            instance={
                "proposed_actions": payload.get("proposed_actions", []),
                "rationale": payload.get("rationale", ""),
            },
            schema=ai_schema,
        )

    def apply_ai_actions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        from training.training_plan_versions.service import TrainingPlanVersionService

        service = TrainingPlanVersionService()
        return service.apply_ai_actions(payload)
