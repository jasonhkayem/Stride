from __future__ import annotations

import uuid
from typing import List

from sqlalchemy import select

from training.common.crud_service import CRUDService
from training.db import SessionLocal

from .models import ActivityLike


class ActivityLikeService(CRUDService):
    def __init__(self):
        super().__init__(ActivityLike, "like_id")

    def list_by_activity(self, activity_id: str) -> List[ActivityLike]:
        with SessionLocal() as session:
            stmt = (
                select(ActivityLike)
                .where(ActivityLike.activity_id == uuid.UUID(str(activity_id)))
                .order_by(ActivityLike.created_at.desc())
            )
            return list(session.execute(stmt).scalars().all())
