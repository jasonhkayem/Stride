from __future__ import annotations

from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields

from training.auth.decorators import require_auth

from .controller import create, create_from_strava, delete, get_by_id, list_all, update
from .schemas import CompletedActionSchema


completed_actions_bp = Blueprint("completed_actions", __name__, url_prefix="/completed_actions")

create_schema = CompletedActionSchema()
update_schema = CompletedActionSchema(partial=True)


class StravaCreateSchema(Schema):
    user_id = fields.UUID(required=True)
    training_plan_action_id = fields.UUID(required=False, allow_none=True)
    source = fields.String(load_default="strava")
    activity = fields.Dict(required=True)


strava_create_schema = StravaCreateSchema()


@completed_actions_bp.route("", methods=["POST"])
@require_auth
def create_route():
    payload = request.get_json(silent=True) or {}

    is_strava_payload = isinstance(payload.get("activity"), dict) or payload.get("source") == "strava"
    if is_strava_payload:
        try:
            validated = strava_create_schema.load(payload)
        except ValidationError as exc:
            return {"errors": exc.messages}, 400
        return create_from_strava(validated)

    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@completed_actions_bp.route("/strava", methods=["POST"])
@require_auth
def create_from_strava_route():
    payload = request.get_json(silent=True) or {}

    if "activity" not in payload:
        activity_payload = dict(payload)
        payload = {
            "user_id": activity_payload.pop("user_id", None),
            "training_plan_action_id": activity_payload.pop("training_plan_action_id", None),
            "source": "strava",
            "activity": activity_payload,
        }

    try:
        validated = strava_create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create_from_strava(validated)


@completed_actions_bp.route("", methods=["GET"])
def list_route():
    return list_all()


@completed_actions_bp.route("/<completed_action_id>", methods=["GET"])
def get_route(completed_action_id: str):
    return get_by_id(completed_action_id)


@completed_actions_bp.route("/<completed_action_id>", methods=["PUT", "PATCH"])
@require_auth
def update_route(completed_action_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(completed_action_id, validated)


@completed_actions_bp.route("/<completed_action_id>", methods=["DELETE"])
@require_auth
def delete_route(completed_action_id: str):
    return delete(completed_action_id)
