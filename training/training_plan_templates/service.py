from __future__ import annotations

from training.common.crud_service import CRUDService

from .models import TrainingPlanTemplate


class TrainingPlanTemplateService(CRUDService):
    def __init__(self):
        super().__init__(TrainingPlanTemplate, "template_id")
