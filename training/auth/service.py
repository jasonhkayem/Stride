from __future__ import annotations

import hashlib
import os
import secrets
import time
import uuid
from typing import Any, Dict

from sqlalchemy import select

from training.db import SessionLocal
from training.users.models import User

_reset_tokens: Dict[str, Dict[str, Any]] = {}
_TOKEN_TTL = 3600  # 1 hour


class AuthError(Exception):
    """Raised when auth fails."""


class AuthService:
    def __init__(self):
        self._salt = os.getenv("AUTH_SALT", "dev-salt")

    def _hash_password(self, raw: str) -> str:
        payload = f"{self._salt}:{raw}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

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

        with SessionLocal() as session:
            user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()

        if user is None:
            return {"message": "If that email is registered, a reset code has been generated."}

        token = secrets.token_urlsafe(32)
        _reset_tokens[token] = {
            "user_id": str(user.user_id),
            "expires_at": int(time.time()) + _TOKEN_TTL,
        }
        return {
            "message": "If that email is registered, a reset code has been generated.",
            "reset_token": token,
        }

    def reset_password(self, token: str, new_password: str) -> User:
        token = (token or "").strip()
        if not token:
            raise AuthError("reset code is required")
        if not new_password or len(new_password) < 8:
            raise AuthError("password must be at least 8 characters")

        record = _reset_tokens.get(token)
        if not record:
            raise AuthError("invalid or expired reset code")
        if int(time.time()) > record["expires_at"]:
            _reset_tokens.pop(token, None)
            raise AuthError("reset code has expired, please request a new one")

        user_id = record["user_id"]
        _reset_tokens.pop(token, None)

        with SessionLocal() as session:
            uid = uuid.UUID(user_id)
            user = session.execute(select(User).where(User.user_id == uid)).scalar_one_or_none()
            if user is None:
                raise AuthError("user not found")
            user.password_hash = self._hash_password(new_password)
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

            hashed = self._hash_password(str(password))
            if hashed != user.password_hash:
                raise AuthError("invalid credentials")

            return user
