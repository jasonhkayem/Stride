from __future__ import annotations

from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields

from .controller import create, delete, get_by_id, list_all, sync_from_strava, update
from .schemas import ActivitySchema


activities_bp = Blueprint("activities", __name__, url_prefix="/activities")

create_schema = ActivitySchema()
update_schema = ActivitySchema(partial=True)


class ActivityStravaSyncSchema(Schema):
    user_id = fields.UUID(required=True)
    per_page = fields.Integer(load_default=30)
    page = fields.Integer(load_default=1)
    max_pages = fields.Integer(load_default=1)
    before = fields.Integer(allow_none=True, load_default=None)
    after = fields.Integer(allow_none=True, load_default=None)


sync_schema = ActivityStravaSyncSchema()


@activities_bp.route("", methods=["POST"])
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@activities_bp.route("", methods=["GET"])
def list_route():
    return list_all()


@activities_bp.route("/<record_id>", methods=["GET"])
def get_route(record_id: str):
    return get_by_id(record_id)


@activities_bp.route("/<record_id>", methods=["PUT", "PATCH"])
def update_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(record_id, validated)


@activities_bp.route("/<record_id>", methods=["DELETE"])
def delete_route(record_id: str):
    return delete(record_id)


@activities_bp.route("/strava/sync", methods=["POST"])
def strava_sync_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = sync_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    validated["user_id"] = str(validated["user_id"])
    return sync_from_strava(validated)
