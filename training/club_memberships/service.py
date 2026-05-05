from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select

from training.common.crud_service import CRUDService
from training.db import SessionLocal

from .models import ClubKickLog, ClubMembership


class ClubMembershipService(CRUDService):
    def __init__(self):
        super().__init__(ClubMembership, "membership_id")

    def list_by_club(self, club_id: str, status: Optional[str] = None) -> List[ClubMembership]:
        with SessionLocal() as session:
            stmt = select(ClubMembership).where(ClubMembership.club_id == uuid.UUID(str(club_id)))
            if status:
                stmt = stmt.where(ClubMembership.status == status)
            stmt = stmt.order_by(ClubMembership.created_at.desc())
            return list(session.execute(stmt).scalars().all())

    def approve_membership(self, membership_id: str) -> ClubMembership:
        with SessionLocal() as session:
            item = session.get(ClubMembership, uuid.UUID(str(membership_id)))
            if item is None:
                raise ValueError("membership not found")
            item.status = "approved"
            item.joined_at = datetime.utcnow()
            session.commit()
            session.refresh(item)
            return item

    def reject_membership(self, membership_id: str) -> ClubMembership:
        with SessionLocal() as session:
            item = session.get(ClubMembership, uuid.UUID(str(membership_id)))
            if item is None:
                raise ValueError("membership not found")
            item.status = "rejected"
            session.commit()
            session.refresh(item)
            return item

    def kick_member(self, membership_id: str, kicked_by: str, reason: Optional[str] = None) -> None:
        with SessionLocal() as session:
            item = session.get(ClubMembership, uuid.UUID(str(membership_id)))
            if item is None:
                raise ValueError("membership not found")
            log = ClubKickLog(
                club_id=item.club_id,
                kicked_user_id=item.user_id,
                kicked_by=uuid.UUID(str(kicked_by)),
                reason=reason or None,
            )
            session.add(log)
            session.delete(item)
            session.commit()

    def list_kick_logs(self, limit: int = 50) -> List[ClubKickLog]:
        with SessionLocal() as session:
            stmt = select(ClubKickLog).order_by(ClubKickLog.created_at.desc()).limit(limit)
            return list(session.execute(stmt).scalars().all())
