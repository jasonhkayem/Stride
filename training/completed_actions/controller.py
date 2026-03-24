from __future__ import annotations

from typing import Any, Dict

from flask import jsonify

from .schemas import CompletedActionSchema
from .service import (
    CompletedActionNotFoundError,
    CompletedActionService,
    CompletedActionValidationError,
)


service = CompletedActionService()
schema = CompletedActionSchema()


def create(payload: Dict[str, Any]):
    try:
        if payload.get("source") == "strava" or isinstance(payload.get("activity"), dict):
            item, created = service.create_from_strava_activity(payload)
            return jsonify(schema.dump(item)), 201 if created else 200
        else:
            item = service.create(payload)
        return jsonify(schema.dump(item)), 201
    except CompletedActionValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def create_from_strava(payload: Dict[str, Any]):
    try:
        item, created = service.create_from_strava_activity(payload)
        return jsonify(schema.dump(item)), 201 if created else 200
    except CompletedActionValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def get_by_id(completed_action_id: str):
    try:
        item = service.get_by_id(completed_action_id)
        if item is None:
            return jsonify({"error": "completed_action not found"}), 404
        return jsonify(schema.dump(item)), 200
    except CompletedActionValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def list_all():
    try:
        items = service.list_all()
        return jsonify(schema.dump(items, many=True)), 200
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def update(completed_action_id: str, payload: Dict[str, Any]):
    try:
        item = service.update(completed_action_id, payload)
        return jsonify(schema.dump(item)), 200
    except CompletedActionNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except CompletedActionValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def delete(completed_action_id: str):
    try:
        service.delete(completed_action_id)
        return jsonify({"status": "deleted"}), 200
    except CompletedActionNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except CompletedActionValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500
