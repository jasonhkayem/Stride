from __future__ import annotations

import json
import logging
import os
import secrets
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import bcrypt
from sqlalchemy import delete, select

from training.auth.models import PasswordResetToken
from training.db import SessionLocal
from training.services.strava_oauth_service import StravaOAuthError, StravaOAuthService
from training.user_integrations.models import UserIntegration
from training.users.models import User
from training.users.schemas import UserSchema

logger = logging.getLogger(__name__)

_TOKEN_TTL_HOURS = 1


def _send_reset_email(to: str, token: str) -> None:
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key:
        logger.warning("RESEND_API_KEY not set — password reset token for %s: %s", to, token)
        return

    payload = json.dumps({
        "from": "Stride <onboarding@resend.dev>",
        "to": to,
        "subject": "Your Stride password reset code",
        "text": (
            f"Your one-time reset code is: {token}\n\n"
            f"This code expires in {_TOKEN_TTL_HOURS} hour(s).\n\n"
            "If you didn't request this, you can safely ignore this email."
        ),
    }).encode()

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Stride/1.0",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as exc:
        logger.error("Resend API error sending to %s: %s %s", to, exc.code, exc.read())
    except Exception as exc:
        logger.error("Failed to send reset email to %s: %s", to, exc)


class AuthError(Exception):
    """Raised when auth fails."""


class AuthService:
    @staticmethod
    def _hash_password(raw: str) -> str:
        return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def _verify_password(raw: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    def signup(self, payload: Dict[str, Any]) -> User:
        name = (payload.get("name") or "").strip()
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or payload.get("password_hash")
        if not name:
            raise AuthError("name is required")
        if not email:
            raise AuthError("email is required")
        if not password:
            raise AuthError("password is required")

        with SessionLocal() as session:
            existing = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if existing is not None:
                raise AuthError("email already exists")

            user = User(
                name=name,
                email=email,
                password_hash=self._hash_password(str(password)),
                platform_role=payload.get("platform_role") or "user",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def forgot_password(self, email: str) -> Dict[str, Any]:
        email = (email or "").strip().lower()
        if not email:
            raise AuthError("email is required")

        generic = {"message": "If that email is registered, a reset link has been sent."}

        with SessionLocal() as session:
            user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if user is None:
                return generic

            # Invalidate any existing tokens for this user first
            session.execute(
                delete(PasswordResetToken).where(PasswordResetToken.user_id == user.user_id)
            )

            token = secrets.token_urlsafe(32)
            record = PasswordResetToken(
                token=token,
                user_id=user.user_id,
                expires_at=datetime.utcnow() + timedelta(hours=_TOKEN_TTL_HOURS),
            )
            session.add(record)
            session.commit()

        _send_reset_email(email, token)
        return generic

    def reset_password(self, token: str, new_password: str) -> User:
        token = (token or "").strip()
        if not token:
            raise AuthError("reset token is required")
        if not new_password or len(new_password) < 8:
            raise AuthError("password must be at least 8 characters")

        with SessionLocal() as session:
            record = session.get(PasswordResetToken, token)
            if record is None:
                raise AuthError("invalid or expired reset token")
            if datetime.utcnow() > record.expires_at:
                session.delete(record)
                session.commit()
                raise AuthError("reset token has expired, please request a new one")

            user_id = record.user_id
            session.delete(record)
            session.flush()

            user = session.execute(select(User).where(User.user_id == user_id)).scalar_one_or_none()
            if user is None:
                raise AuthError("user not found")
            user.password_hash = self._hash_password(new_password)
            session.commit()
            session.refresh(user)
            return user

    def strava_oauth_login(self, code: str, state: str) -> User:
        """Find-or-create a User via Strava OAuth. Returns the User object."""
        oauth = StravaOAuthService()
        state_info = oauth.validate_state(state)
        if state_info.get("type") != "auth":
            raise AuthError("Invalid OAuth state type for sign-in flow")

        token_payload = oauth.exchange_code(code)
        access_token = token_payload.get("access_token")
        refresh_token = token_payload.get("refresh_token")
        scope = token_payload.get("scope")

        expires_at_epoch = token_payload.get("expires_at")
        try:
            expires_at = (
                datetime.fromtimestamp(int(expires_at_epoch), tz=timezone.utc).replace(tzinfo=None)
                if expires_at_epoch
                else None
            )
        except (TypeError, ValueError):
            expires_at = None

        athlete = token_payload.get("athlete") or oauth.fetch_athlete(access_token)
        athlete_id = str(athlete.get("id", ""))
        if not athlete_id:
            raise AuthError("Strava response missing athlete id")

        name = (
            f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
            or "Strava Athlete"
        )

        with SessionLocal() as session:
            user = session.execute(
                select(User).where(User.strava_athlete_id == athlete_id)
            ).scalar_one_or_none()

            if user is None:
                user = User(
                    name=name,
                    email=f"strava_{athlete_id}@stride.local",
                    password_hash=self._hash_password(secrets.token_urlsafe(32)),
                    platform_role="user",
                    strava_athlete_id=athlete_id,
                    strava_connected_at=datetime.utcnow(),
                )
                session.add(user)
                session.flush()
            else:
                user.strava_connected_at = datetime.utcnow()

            integration = session.execute(
                select(UserIntegration).where(
                    UserIntegration.user_id == user.user_id,
                    UserIntegration.provider == "strava",
                )
            ).scalar_one_or_none()

            if integration is None:
                integration = UserIntegration(
                    user_id=user.user_id,
                    provider="strava",
                    external_user_id=athlete_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expires_at=expires_at,
                    scopes=scope,
                )
                session.add(integration)
            else:
                integration.access_token = access_token
                integration.refresh_token = refresh_token
                integration.token_expires_at = expires_at
                integration.scopes = scope

            session.commit()
            session.refresh(user)
            return user

    def login(self, payload: Dict[str, Any]) -> User:
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password")
        if not email:
            raise AuthError("email is required")
        if not password:
            raise AuthError("password is required")

        with SessionLocal() as session:
            user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if user is None:
                raise AuthError("invalid credentials")

            if not self._verify_password(str(password), user.password_hash):
                raise AuthError("invalid credentials")

            return user
