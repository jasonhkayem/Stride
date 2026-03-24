from __future__ import annotations

from training.common.crud_service import CRUDService

from .models import Message


class MessageService(CRUDService):
    def __init__(self):
        super().__init__(Message, "message_id")
