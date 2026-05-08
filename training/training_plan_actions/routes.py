from __future__ import annotations

from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields

from training.auth.decorators import require_auth

from .controller import apply_ai_actions, create, delete, get_by_id, list_all, update
from .schemas import TrainingPlanActionSchema


training_plan_actions_bp = Blueprint("training_plan_actions", __name__, url_prefix="/training_plan_actions")

create_schema = TrainingPlanActionSchema()
update_schema = TrainingPlanActionSchema(partial=True)


class ApplyAiActionsSchema(Schema):
    version_id = fields.UUID(required=True)
    proposed_actions = fields.List(fields.Dict(), required=True)
    rationale = fields.String(required=True)


apply_schema = ApplyAiActionsSchema()


@training_plan_actions_bp.route("", methods=["POST"])
@require_auth
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@training_plan_actions_bp.route("", methods=["GET"])
def list_route():
    return list_all()


@training_plan_actions_bp.route("/<record_id>", methods=["GET"])
def get_route(record_id: str):
    return get_by_id(record_id)


@training_plan_actions_bp.route("/apply_ai_actions", methods=["POST"])
@require_auth
def apply_ai_actions_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = apply_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return apply_ai_actions(validated)


@training_plan_actions_bp.route("/<record_id>", methods=["PUT", "PATCH"])
@require_auth
def update_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(record_id, validated)


@training_plan_actions_bp.route("/<record_id>", methods=["DELETE"])
@require_auth
def delete_route(record_id: str):
    return delete(record_id)
