from __future__ import annotations

from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields

from training.auth.decorators import require_auth

from .controller import bulk_create, create, delete, get_by_id, list_all, update
from .schemas import CompletedActionLapSchema


completed_action_laps_bp = Blueprint("completed_action_laps", __name__, url_prefix="/completed_action_laps")

create_schema = CompletedActionLapSchema()
update_schema = CompletedActionLapSchema(partial=True)


class BulkLapsSchema(Schema):
    completed_action_id = fields.UUID(required=True)
    laps = fields.List(fields.Nested(CompletedActionLapSchema(exclude=("completed_action_id",))), required=True)


bulk_laps_schema = BulkLapsSchema()


@completed_action_laps_bp.route("", methods=["POST"])
@require_auth
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@completed_action_laps_bp.route("/bulk", methods=["POST"])
@require_auth
def bulk_create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = bulk_laps_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return bulk_create(str(validated["completed_action_id"]), validated["laps"])


@completed_action_laps_bp.route("", methods=["GET"])
def list_route():
    return list_all()


@completed_action_laps_bp.route("/<lap_id>", methods=["GET"])
def get_route(lap_id: str):
    return get_by_id(lap_id)


@completed_action_laps_bp.route("/<lap_id>", methods=["PUT", "PATCH"])
@require_auth
def update_route(lap_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(lap_id, validated)


@completed_action_laps_bp.route("/<lap_id>", methods=["DELETE"])
@require_auth
def delete_route(lap_id: str):
    return delete(lap_id)
