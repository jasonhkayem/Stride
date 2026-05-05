from __future__ import annotations

import uuid
from typing import Any, Dict

from flask import jsonify
from sqlalchemy import select

from training.db import SessionLocal
from training.users.models import User
from training.users.schemas import UserSchema

from .jwt_utils import generate_token
from .service import AuthError, AuthService


service = AuthService()
schema = UserSchema()


def signup(payload: Dict[str, Any]):
    try:
        user = service.signup(payload)
        token = generate_token(str(user.user_id), user.platform_role)
        return jsonify({"token": token, "user": schema.dump(user)}), 201
    except AuthError as exc:
        message = str(exc)
        status = 409 if "exists" in message else 400
        return jsonify({"error": message}), status
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def login(payload: Dict[str, Any]):
    try:
        user = service.login(payload)
        token = generate_token(str(user.user_id), user.platform_role)
        return jsonify({"token": token, "user": schema.dump(user)}), 200
    except AuthError as exc:
        return jsonify({"error": str(exc)}), 401
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def forgot_password(payload: Dict[str, Any]):
    try:
        result = service.forgot_password(payload.get("email", ""))
        return jsonify(result), 200
    except AuthError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def reset_password(payload: Dict[str, Any]):
    try:
        service.reset_password(payload.get("token", ""), payload.get("new_password", ""))
        return jsonify({"message": "Password reset successfully. You can now sign in."}), 200
    except AuthError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def me(user_id: str):
    try:
        uid = uuid.UUID(user_id)
        with SessionLocal() as session:
            user = session.execute(
                select(User).where(User.user_id == uid)
            ).scalar_one_or_none()
        if user is None:
            return jsonify({"error": "user not found"}), 404
        return jsonify(schema.dump(user)), 200
    except (ValueError, AttributeError):
        return jsonify({"error": "invalid user id"}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500
