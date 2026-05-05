from __future__ import annotations

from typing import Any, Dict

from flask import g, jsonify
from sqlalchemy.exc import IntegrityError

from training.common.crud_service import NotFoundError

from .schemas import ClubSchema
from .service import ClubService


service = ClubService()
schema = ClubSchema()


def create(payload: Dict[str, Any]):
    payload.setdefault("created_by", g.current_user_id)
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
    club = service.get_by_id(record_id)
    if club is None:
        return jsonify({"error": "record not found"}), 404
    if str(club.created_by) != g.current_user_id and g.current_role != "super_admin":
        return jsonify({"error": "forbidden"}), 403
    try:
        service.delete(record_id)
        return jsonify({"status": "deleted"}), 200
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500
