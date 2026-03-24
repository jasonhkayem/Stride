from __future__ import annotations

from training.common.crud_service import CRUDService

from .models import Club


class ClubService(CRUDService):
    def __init__(self):
        super().__init__(Club, "club_id")
