from __future__ import annotations

from typing import Any, Dict

from flask import g, jsonify
from sqlalchemy.exc import IntegrityError

from training.common.crud_service import NotFoundError

from .schemas import ActivitySchema
from .service import ActivityService, ActivitySyncError


service = ActivityService()
schema = ActivitySchema()


def _check_activity_ownership(record_id: str):
    """Return (activity, None) if caller owns it, or (None, error_response)."""
    activity = service.get_by_id(record_id)
    if activity is None:
        return None, (jsonify({"error": "record not found"}), 404)
    if str(activity.user_id) != g.current_user_id:
        return None, (jsonify({"error": "forbidden"}), 403)
    return activity, None


def create(payload: Dict[str, Any]):
    try:
        item = service.create(payload)
        return jsonify(schema.dump(item)), 201
    except IntegrityError as exc:
        return jsonify({"error": "conflict", "detail": str(exc.orig)}), 409
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def get_by_id(record_id: str):
    try:
        item = service.get_by_id(record_id)
        if item is None:
            return jsonify({"error": "record not found"}), 404
        return jsonify(schema.dump(item)), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def list_all():
    try:
        items = service.list_all()
        return jsonify(schema.dump(items, many=True)), 200
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def update(record_id: str, payload: Dict[str, Any]):
    _, err = _check_activity_ownership(record_id)
    if err:
        return err
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
    _, err = _check_activity_ownership(record_id)
    if err:
        return err
    try:
        service.delete(record_id)
        return jsonify({"status": "deleted"}), 200
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def sync_from_strava(payload: Dict[str, Any]):
    try:
        result = service.sync_from_strava(
            user_id=g.current_user_id,
            per_page=payload.get("per_page", 30),
            page=payload.get("page", 1),
            max_pages=payload.get("max_pages", 1),
            before=payload.get("before"),
            after=payload.get("after"),
        )
        return jsonify(result), 200
    except ActivitySyncError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500
