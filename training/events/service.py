from __future__ import annotations

import uuid
from typing import Any, Dict

from sqlalchemy import select

from training.common.crud_service import CRUDService
from training.db import SessionLocal
from training.club_memberships.models import ClubMembership
from training.users.models import User

from .models import Event


class EventService(CRUDService):
    def __init__(self):
        super().__init__(Event, "event_id")

    def create(self, payload: Dict[str, Any]):
        club_id = payload.get("club_id")
        created_by = payload.get("created_by")
        if not club_id:
            raise ValueError("club_id is required")
        if not created_by:
            raise ValueError("created_by is required")

        with SessionLocal() as session:
            membership = session.execute(
                select(ClubMembership).where(
                    ClubMembership.club_id == uuid.UUID(str(club_id)),
                    ClubMembership.user_id == uuid.UUID(str(created_by)),
                    ClubMembership.role == "club_admin",
                    ClubMembership.status == "approved",
                )
            ).scalar_one_or_none()

            if membership is None:
                raise ValueError("only approved club_admin can create events")

        data = dict(payload)
        data.pop("created_by", None)
        return super().create(data)
