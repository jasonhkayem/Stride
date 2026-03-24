from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select

from training.common.crud_service import CRUDService
from training.db import SessionLocal

from .models import ClubMembership


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
