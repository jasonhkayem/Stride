from __future__ import annotations

from flask import Blueprint, request
from marshmallow import ValidationError

from training.auth.decorators import require_auth

from .controller import create, delete, get_by_id, list_all, update
from .schemas import TrainingPlanTemplateSchema


training_plan_templates_bp = Blueprint("training_plan_templates", __name__, url_prefix="/training_plan_templates")

create_schema = TrainingPlanTemplateSchema()
update_schema = TrainingPlanTemplateSchema(partial=True)


@training_plan_templates_bp.route("", methods=["POST"])
@require_auth
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@training_plan_templates_bp.route("", methods=["GET"])
def list_route():
    return list_all()


@training_plan_templates_bp.route("/<record_id>", methods=["GET"])
def get_route(record_id: str):
    return get_by_id(record_id)


@training_plan_templates_bp.route("/<record_id>", methods=["PUT", "PATCH"])
@require_auth
def update_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(record_id, validated)


@training_plan_templates_bp.route("/<record_id>", methods=["DELETE"])
@require_auth
def delete_route(record_id: str):
    return delete(record_id)
