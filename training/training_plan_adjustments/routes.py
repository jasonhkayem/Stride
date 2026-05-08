from __future__ import annotations

from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields

from training.auth.decorators import require_auth

from .controller import create, delete, get_by_id, list_all, update
from .schemas import TrainingPlanAdjustmentSchema


training_plan_adjustments_bp = Blueprint(
    "training_plan_adjustments",
    __name__,
    url_prefix="/training_plan_adjustments",
)

create_schema = TrainingPlanAdjustmentSchema()
update_schema = TrainingPlanAdjustmentSchema(partial=True)


class ApplySuggestionSchema(Schema):
    apply = fields.Boolean(load_default=False)


apply_schema = ApplySuggestionSchema()


@training_plan_adjustments_bp.route("", methods=["POST"])
@require_auth
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@training_plan_adjustments_bp.route("", methods=["GET"])
def list_route():
    return list_all()


@training_plan_adjustments_bp.route("/<adjustment_id>", methods=["GET"])
def get_route(adjustment_id: str):
    return get_by_id(adjustment_id)


@training_plan_adjustments_bp.route("/<adjustment_id>", methods=["PUT", "PATCH"])
@require_auth
def update_route(adjustment_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(adjustment_id, validated)


@training_plan_adjustments_bp.route("/<adjustment_id>/apply", methods=["POST"])
@require_auth
def apply_route(adjustment_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        apply_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(adjustment_id, {"status": "approved"})


@training_plan_adjustments_bp.route("/<adjustment_id>", methods=["DELETE"])
@require_auth
def delete_route(adjustment_id: str):
    return delete(adjustment_id)
