from __future__ import annotations

from typing import Any, Dict

from flask import jsonify

from .schemas import TrainingPlanAdjustmentSchema
from .service import (
    TrainingPlanAdjustmentNotFoundError,
    TrainingPlanAdjustmentService,
    TrainingPlanAdjustmentValidationError,
)


service = TrainingPlanAdjustmentService()
schema = TrainingPlanAdjustmentSchema()


def create(payload: Dict[str, Any]):
    try:
        item = service.create(payload)
        return jsonify(schema.dump(item)), 201
    except TrainingPlanAdjustmentValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def get_by_id(adjustment_id: str):
    try:
        item = service.get_by_id(adjustment_id)
        if item is None:
            return jsonify({"error": "training_plan_adjustment not found"}), 404
        return jsonify(schema.dump(item)), 200
    except TrainingPlanAdjustmentValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def list_all():
    try:
        items = service.list_all()
        return jsonify(schema.dump(items, many=True)), 200
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def update(adjustment_id: str, payload: Dict[str, Any]):
    try:
        item = service.update(adjustment_id, payload)
        return jsonify(schema.dump(item)), 200
    except TrainingPlanAdjustmentNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except TrainingPlanAdjustmentValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def delete(adjustment_id: str):
    try:
        service.delete(adjustment_id)
        return jsonify({"status": "deleted"}), 200
    except TrainingPlanAdjustmentNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except TrainingPlanAdjustmentValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500
