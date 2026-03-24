from __future__ import annotations

from typing import Any, Dict

from training.training_plan_versions.service import TrainingPlanVersionService


class PlanVersioningService:
    """
    Applies validated AI actions and creates new plan versions.
    """

    def __init__(self) -> None:
        self._version_service = TrainingPlanVersionService()

    def apply_validated_actions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new training plan version and matching action rows.
        """
        return self._version_service.apply_ai_actions(payload)
