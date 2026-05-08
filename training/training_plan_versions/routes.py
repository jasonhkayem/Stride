from __future__ import annotations

from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields

from training.auth.decorators import require_auth

from .controller import apply_ai_actions, create, delete, generate_from_template, generate_plan, get_by_id, list_all, update, validate_ai_actions
from .schemas import TrainingPlanVersionSchema


training_plan_versions_bp = Blueprint("training_plan_versions", __name__, url_prefix="/training_plan_versions")

create_schema = TrainingPlanVersionSchema()
update_schema = TrainingPlanVersionSchema(partial=True)


class ApplyAiActionsSchema(Schema):
    version_id = fields.UUID(required=True)
    proposed_actions = fields.List(fields.Dict(), required=True)
    rationale = fields.String(required=True)


apply_schema = ApplyAiActionsSchema()


class AiActionsSchema(Schema):
    version_id = fields.UUID(required=True)
    proposed_actions = fields.List(fields.Dict(), required=True)
    rationale = fields.String(required=True)
    apply = fields.Boolean(load_default=False)


ai_actions_schema = AiActionsSchema()


class GeneratePlanSchema(Schema):
    user_plan_id = fields.UUID(required=True)
    race_distance = fields.String(required=True)
    race_date = fields.Date(required=True)
    goal_type = fields.String(required=True)
    goal_time = fields.String(allow_none=True)
    experience_level = fields.String(required=True)
    runs_per_week = fields.Integer(required=True)
    previous_pb = fields.String(allow_none=True)
    notes = fields.String(allow_none=True)


generate_schema = GeneratePlanSchema()


class GenerateFromTemplateSchema(Schema):
    user_plan_id = fields.UUID(required=True)
    template_id = fields.UUID(required=True)
    goal_time = fields.String(required=True)
    reset = fields.Boolean(load_default=False)


generate_from_template_schema = GenerateFromTemplateSchema()


@training_plan_versions_bp.route("", methods=["POST"])
@require_auth
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@training_plan_versions_bp.route("", methods=["GET"])
def list_route():
    include_related = request.args.get("include_related", "false").lower() == "true"
    return list_all(include_related=include_related)


@training_plan_versions_bp.route("/<record_id>", methods=["GET"])
def get_route(record_id: str):
    include_related = request.args.get("include_related", "false").lower() == "true"
    return get_by_id(record_id, include_related=include_related)


@training_plan_versions_bp.route("/<record_id>/full", methods=["GET"])
def get_full_route(record_id: str):
    return get_by_id(record_id, include_related=True)


@training_plan_versions_bp.route("/apply_ai_actions", methods=["POST"])
@require_auth
def apply_ai_actions_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = apply_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return apply_ai_actions(validated)


@training_plan_versions_bp.route("/ai_actions", methods=["POST"])
@require_auth
def ai_actions_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = ai_actions_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400

    if validated.get("apply"):
        return apply_ai_actions(validated)
    return validate_ai_actions(validated)


@training_plan_versions_bp.route("/generate", methods=["POST"])
@require_auth
def generate_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = generate_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    validated["user_plan_id"] = str(validated["user_plan_id"])
    validated["race_date"] = validated["race_date"].isoformat()
    return generate_plan(validated)


@training_plan_versions_bp.route("/generate_from_template", methods=["POST"])
@require_auth
def generate_from_template_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = generate_from_template_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    validated["user_plan_id"] = str(validated["user_plan_id"])
    validated["template_id"] = str(validated["template_id"])
    return generate_from_template(validated)


@training_plan_versions_bp.route("/<record_id>", methods=["PUT", "PATCH"])
@require_auth
def update_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(record_id, validated)


@training_plan_versions_bp.route("/<record_id>", methods=["DELETE"])
@require_auth
def delete_route(record_id: str):
    return delete(record_id)
