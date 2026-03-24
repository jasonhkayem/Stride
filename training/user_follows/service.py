from __future__ import annotations

import uuid
from typing import Any, Dict, List

from sqlalchemy import select

from training.common.crud_service import CRUDService
from training.db import SessionLocal

from .models import UserFollow


class UserFollowService(CRUDService):
    def __init__(self):
        super().__init__(UserFollow, "follow_id")

    def create(self, payload: Dict[str, Any]):
        follower_id = uuid.UUID(str(payload.get("follower_id")))
        following_id = uuid.UUID(str(payload.get("following_id")))

        if follower_id == following_id:
            raise ValueError("Users cannot follow themselves")

        with SessionLocal() as session:
            existing = session.execute(
                select(UserFollow).where(
                    UserFollow.follower_id == follower_id,
                    UserFollow.following_id == following_id,
                )
            ).scalar_one_or_none()
            if existing is not None:
                raise ValueError("Follow relationship already exists")

            item = UserFollow(follower_id=follower_id, following_id=following_id)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def list_followers(self, user_id: str) -> List[UserFollow]:
        with SessionLocal() as session:
            stmt = (
                select(UserFollow)
                .where(UserFollow.following_id == uuid.UUID(str(user_id)))
                .order_by(UserFollow.created_at.desc())
            )
            return list(session.execute(stmt).scalars().all())

    def list_following(self, user_id: str) -> List[UserFollow]:
        with SessionLocal() as session:
            stmt = (
                select(UserFollow)
                .where(UserFollow.follower_id == uuid.UUID(str(user_id)))
                .order_by(UserFollow.created_at.desc())
            )
            return list(session.execute(stmt).scalars().all())
