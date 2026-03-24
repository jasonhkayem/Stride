from __future__ import annotations

from typing import Any, Dict

from flask import jsonify

from training.users.schemas import UserSchema

from .service import AuthError, AuthService


service = AuthService()
schema = UserSchema()


def signup(payload: Dict[str, Any]):
    try:
        user = service.signup(payload)
        return jsonify(schema.dump(user)), 201
    except AuthError as exc:
        message = str(exc)
        status = 409 if "exists" in message else 400
        return jsonify({"error": message}), status
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def login(payload: Dict[str, Any]):
    try:
        user = service.login(payload)
        return jsonify(schema.dump(user)), 200
    except AuthError as exc:
        return jsonify({"error": str(exc)}), 401
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def me(user_id: str):
    try:
        user = service.get_by_id(user_id)
        if user is None:
            return jsonify({"error": "user not found"}), 404
        return jsonify(schema.dump(user)), 200
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500
