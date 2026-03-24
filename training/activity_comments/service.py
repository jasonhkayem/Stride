from __future__ import annotations

import uuid
from typing import Any, Dict, List

from sqlalchemy import select

from training.common.crud_service import CRUDService
from training.db import SessionLocal

from .models import ActivityComment


class ActivityCommentService(CRUDService):
    def __init__(self):
        super().__init__(ActivityComment, "comment_id")

    def create(self, payload: Dict[str, Any]):
        parent_comment_id = payload.get("parent_comment_id")
        if parent_comment_id is None:
            return super().create(payload)

        with SessionLocal() as session:
            parent_id = uuid.UUID(str(parent_comment_id))
            parent = session.execute(
                select(ActivityComment).where(ActivityComment.comment_id == parent_id)
            ).scalar_one_or_none()
            if parent is None:
                raise ValueError("parent_comment_id does not exist")

            activity_id = uuid.UUID(str(payload.get("activity_id")))
            if activity_id != parent.activity_id:
                raise ValueError("Reply must target a comment on the same activity")

            item = ActivityComment(**payload)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def list_replies(self, parent_comment_id: str) -> List[ActivityComment]:
        with SessionLocal() as session:
            stmt = (
                select(ActivityComment)
                .where(ActivityComment.parent_comment_id == uuid.UUID(str(parent_comment_id)))
                .order_by(ActivityComment.created_at.asc())
            )
            return list(session.execute(stmt).scalars().all())

    def list_by_activity(self, activity_id: str) -> List[ActivityComment]:
        with SessionLocal() as session:
            stmt = (
                select(ActivityComment)
                .where(ActivityComment.activity_id == uuid.UUID(str(activity_id)))
                .order_by(ActivityComment.created_at.desc())
            )
            return list(session.execute(stmt).scalars().all())
