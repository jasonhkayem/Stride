from __future__ import annotations

from training.common.crud_service import CRUDService

from .models import EventRegistration


class EventRegistrationService(CRUDService):
    def __init__(self):
        super().__init__(EventRegistration, "registration_id")
