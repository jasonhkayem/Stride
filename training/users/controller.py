from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict

from flask import g, jsonify, request

from training.common.crud_service import NotFoundError
from training.services.strava_oauth_service import StravaOAuthError

from .schemas import UserSchema
from .service import UserService

_IMAGES_DIR = Path(__file__).resolve().parent.parent.parent / "images"
_ALLOWED_IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp"}


service = UserService()
schema = UserSchema()


def create(payload: Dict[str, Any]):
    try:
        item = service.create(payload)
        return jsonify(schema.dump(item)), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def get_by_id(record_id: str, include_related: bool = False):
    try:
        if include_related:
            item = service.get_with_related(record_id)
            if item is None:
                return jsonify({"error": "record not found"}), 404
            return jsonify(item), 200

        item = service.get_by_id(record_id)
        if item is None:
            return jsonify({"error": "record not found"}), 404
        return jsonify(schema.dump(item)), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def list_all(include_related: bool = False):
    try:
        if include_related:
            return jsonify(service.list_all_with_related()), 200
        items = service.list_all()
        return jsonify(schema.dump(items, many=True)), 200
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def search_by_username(query: str, limit: int = 10):
    try:
        items = service.search_by_username(query=query, limit=limit)
        return jsonify(schema.dump(items, many=True)), 200
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def update(record_id: str, payload: Dict[str, Any]):
    if g.current_user_id != record_id and g.current_role != "super_admin":
        return jsonify({"error": "forbidden"}), 403
    try:
        item = service.update(record_id, payload)
        return jsonify(schema.dump(item)), 200
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def delete(record_id: str):
    try:
        service.delete(record_id)
        return jsonify({"status": "deleted"}), 200
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def upload_avatar(record_id: str):
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in _ALLOWED_IMAGE_EXTS:
        return jsonify({"error": "File type not allowed. Use JPG, PNG, GIF, or WebP"}), 400
    avatars_dir = _IMAGES_DIR / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)
    filename = f"avatar_{record_id}_{uuid.uuid4().hex}.{ext}"
    file.save(str(avatars_dir / filename))
    profile_picture_url = f"/images/avatars/{filename}"
    try:
        item = service.update(record_id, {"profile_picture_url": profile_picture_url})
        return jsonify(schema.dump(item)), 200
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def strava_authorize(record_id: str):
    try:
        result = service.get_strava_authorize_url(record_id)
        return jsonify(result), 200
    except StravaOAuthError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def strava_connect(record_id: str, payload: Dict[str, Any]):
    try:
        result = service.connect_strava_oauth(
            user_id=record_id,
            code=payload.get("code"),
            state=payload.get("state"),
        )
        return jsonify(result), 200
    except StravaOAuthError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message else 400
        return jsonify({"error": message}), status
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def strava_connect_callback(payload: Dict[str, Any]):
    try:
        result = service.connect_strava_oauth_from_state(
            code=payload.get("code"),
            state=payload.get("state"),
        )
        return jsonify(result), 200
    except StravaOAuthError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message else 400
        return jsonify({"error": message}), status
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def strava_status(record_id: str):
    try:
        result = service.get_strava_connection(record_id)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def strava_disconnect(record_id: str):
    try:
        result = service.disconnect_strava(record_id)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500
