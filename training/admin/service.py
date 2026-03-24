from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Date, and_, cast, func, or_, select

from training.activities.models import Activity
from training.activity_comments.models import ActivityComment
from training.chatbot_session_messages.models import ChatbotSessionMessage
from training.chatbot_sessions.models import ChatbotSession
from training.db import SessionLocal
from training.user_follows.models import UserFollow
from training.users.models import User


class AdminAuthError(Exception):
    """Raised when admin authentication/authorization fails."""


class AdminDashboardService:
    def _require_super_admin(self, admin_user_id: str) -> User:
        if not admin_user_id:
            raise AdminAuthError("Missing X-Admin-User-Id header")

        try:
            uid = uuid.UUID(str(admin_user_id))
        except (ValueError, TypeError) as exc:
            raise AdminAuthError("X-Admin-User-Id must be a valid UUID") from exc

        with SessionLocal() as session:
            user = session.get(User, uid)
            if user is None:
                raise AdminAuthError("Admin user not found")
            if user.platform_role != "super_admin":
                raise AdminAuthError("User is not authorized for admin dashboard")
            return user

    @staticmethod
    def _parse_days(days: int) -> int:
        if days < 1 or days > 365:
            raise ValueError("days must be between 1 and 365")
        return days

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    def overview(self, admin_user_id: str, days: int = 30) -> Dict[str, Any]:
        self._require_super_admin(admin_user_id)
        days = self._parse_days(days)
        since = self._utc_now() - timedelta(days=days)

        with SessionLocal() as session:
            total_users = session.execute(select(func.count(User.user_id))).scalar_one()
            total_activities = session.execute(select(func.count(Activity.activity_id))).scalar_one()
            total_comments = session.execute(select(func.count(ActivityComment.comment_id))).scalar_one()
            total_follows = session.execute(select(func.count(UserFollow.follow_id))).scalar_one()
            total_chat_sessions = session.execute(select(func.count(ChatbotSession.chatbot_id))).scalar_one()
            total_chat_messages = session.execute(
                select(func.count(ChatbotSessionMessage.message_id))
            ).scalar_one()

            new_users_last_period = session.execute(
                select(func.count(User.user_id)).where(User.created_at >= since)
            ).scalar_one()
            activities_last_period = session.execute(
                select(func.count(Activity.activity_id)).where(Activity.created_at >= since)
            ).scalar_one()
            chat_messages_last_period = session.execute(
                select(func.count(ChatbotSessionMessage.message_id)).where(
                    ChatbotSessionMessage.created_at >= since
                )
            ).scalar_one()

            active_users_last_30_days = session.execute(
                select(func.count(func.distinct(Activity.user_id))).where(
                    Activity.created_at >= (self._utc_now() - timedelta(days=30))
                )
            ).scalar_one()

            return {
                "window_days": days,
                "totals": {
                    "users": int(total_users or 0),
                    "activities": int(total_activities or 0),
                    "comments_and_replies": int(total_comments or 0),
                    "follows": int(total_follows or 0),
                    "chatbot_sessions": int(total_chat_sessions or 0),
                    "chatbot_messages": int(total_chat_messages or 0),
                },
                "window": {
                    "new_users": int(new_users_last_period or 0),
                    "activities": int(activities_last_period or 0),
                    "chatbot_messages": int(chat_messages_last_period or 0),
                },
                "active_users_30d": int(active_users_last_30_days or 0),
            }

    def trends(self, admin_user_id: str, days: int = 30) -> Dict[str, Any]:
        self._require_super_admin(admin_user_id)
        days = self._parse_days(days)
        since = (self._utc_now() - timedelta(days=days)).date()

        with SessionLocal() as session:
            users_rows = session.execute(
                select(cast(User.created_at, Date).label("day"), func.count(User.user_id).label("count"))
                .where(cast(User.created_at, Date) >= since)
                .group_by(cast(User.created_at, Date))
                .order_by(cast(User.created_at, Date))
            ).all()

            activities_rows = session.execute(
                select(cast(Activity.created_at, Date).label("day"), func.count(Activity.activity_id).label("count"))
                .where(cast(Activity.created_at, Date) >= since)
                .group_by(cast(Activity.created_at, Date))
                .order_by(cast(Activity.created_at, Date))
            ).all()

            chat_rows = session.execute(
                select(
                    cast(ChatbotSessionMessage.created_at, Date).label("day"),
                    func.count(ChatbotSessionMessage.message_id).label("count"),
                )
                .where(cast(ChatbotSessionMessage.created_at, Date) >= since)
                .group_by(cast(ChatbotSessionMessage.created_at, Date))
                .order_by(cast(ChatbotSessionMessage.created_at, Date))
            ).all()

            def _serialize(rows):
                return [{"day": r.day.isoformat(), "count": int(r.count)} for r in rows]

            return {
                "window_days": days,
                "new_users": _serialize(users_rows),
                "activities": _serialize(activities_rows),
                "chatbot_messages": _serialize(chat_rows),
            }

    def top_users(self, admin_user_id: str, limit: int = 10) -> Dict[str, Any]:
        self._require_super_admin(admin_user_id)
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        with SessionLocal() as session:
            activity_subq = (
                select(Activity.user_id.label("user_id"), func.count(Activity.activity_id).label("activities_count"))
                .group_by(Activity.user_id)
                .subquery()
            )
            comment_subq = (
                select(ActivityComment.user_id.label("user_id"), func.count(ActivityComment.comment_id).label("comments_count"))
                .group_by(ActivityComment.user_id)
                .subquery()
            )
            follower_subq = (
                select(UserFollow.following_id.label("user_id"), func.count(UserFollow.follow_id).label("followers_count"))
                .group_by(UserFollow.following_id)
                .subquery()
            )

            rows = session.execute(
                select(
                    User.user_id,
                    User.name,
                    User.email,
                    func.coalesce(activity_subq.c.activities_count, 0).label("activities_count"),
                    func.coalesce(comment_subq.c.comments_count, 0).label("comments_count"),
                    func.coalesce(follower_subq.c.followers_count, 0).label("followers_count"),
                )
                .outerjoin(activity_subq, activity_subq.c.user_id == User.user_id)
                .outerjoin(comment_subq, comment_subq.c.user_id == User.user_id)
                .outerjoin(follower_subq, follower_subq.c.user_id == User.user_id)
                .order_by(
                    func.coalesce(activity_subq.c.activities_count, 0).desc(),
                    func.coalesce(comment_subq.c.comments_count, 0).desc(),
                    User.created_at.asc(),
                )
                .limit(limit)
            ).all()

            items = []
            for r in rows:
                items.append(
                    {
                        "user_id": str(r.user_id),
                        "name": r.name,
                        "email": r.email,
                        "activities_count": int(r.activities_count),
                        "comments_count": int(r.comments_count),
                        "followers_count": int(r.followers_count),
                    }
                )

            return {"limit": limit, "items": items}

    def users_monitoring(
        self,
        admin_user_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        self._require_super_admin(admin_user_id)

        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1 or page_size > 200:
            raise ValueError("page_size must be between 1 and 200")

        with SessionLocal() as session:
            activity_subq = (
                select(Activity.user_id.label("user_id"), func.count(Activity.activity_id).label("activities_count"), func.max(Activity.created_at).label("last_activity_at"))
                .group_by(Activity.user_id)
                .subquery()
            )
            follower_subq = (
                select(UserFollow.following_id.label("user_id"), func.count(UserFollow.follow_id).label("followers_count"))
                .group_by(UserFollow.following_id)
                .subquery()
            )

            filters = []
            if search:
                pattern = f"%{search.strip()}%"
                filters.append(or_(User.name.ilike(pattern), User.email.ilike(pattern)))
            if from_date is not None:
                filters.append(cast(User.created_at, Date) >= from_date)
            if to_date is not None:
                filters.append(cast(User.created_at, Date) <= to_date)

            base_stmt = (
                select(
                    User.user_id,
                    User.name,
                    User.email,
                    User.platform_role,
                    User.created_at,
                    User.updated_at,
                    func.coalesce(activity_subq.c.activities_count, 0).label("activities_count"),
                    activity_subq.c.last_activity_at,
                    func.coalesce(follower_subq.c.followers_count, 0).label("followers_count"),
                )
                .outerjoin(activity_subq, activity_subq.c.user_id == User.user_id)
                .outerjoin(follower_subq, follower_subq.c.user_id == User.user_id)
            )

            if filters:
                base_stmt = base_stmt.where(and_(*filters))

            total = session.execute(select(func.count()).select_from(base_stmt.subquery())).scalar_one()

            rows = session.execute(
                base_stmt
                .order_by(User.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()

            items: List[Dict[str, Any]] = []
            for r in rows:
                items.append(
                    {
                        "user_id": str(r.user_id),
                        "name": r.name,
                        "email": r.email,
                        "platform_role": r.platform_role,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                        "activities_count": int(r.activities_count),
                        "followers_count": int(r.followers_count),
                        "last_activity_at": r.last_activity_at.isoformat() if r.last_activity_at else None,
                    }
                )

            return {
                "page": page,
                "page_size": page_size,
                "total": int(total or 0),
                "items": items,
            }
