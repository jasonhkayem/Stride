from __future__ import annotations

import hashlib
import os
from typing import Any, Dict

from sqlalchemy import select

from training.db import SessionLocal
from training.users.models import User


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

    def login(self, payload: Dict[str, Any]) -> User:
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password")
        if not email:
            raise AuthError("email is required")

        with SessionLocal() as session:
            user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if user is None:
                raise AuthError("invalid credentials")

            if password:
                hashed = self._hash_password(str(password))
                if hashed != user.password_hash:
                    raise AuthError("invalid credentials")

            return user
