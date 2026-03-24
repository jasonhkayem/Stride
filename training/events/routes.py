from __future__ import annotations

from flask import Blueprint, request
from marshmallow import ValidationError

from .controller import create, delete, get_by_id, list_all, update
from .schemas import EventSchema


events_bp = Blueprint("events", __name__, url_prefix="/events")

create_schema = EventSchema()
update_schema = EventSchema(partial=True)


@events_bp.route("", methods=["POST"])
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@events_bp.route("", methods=["GET"])
def list_route():
    return list_all()


@events_bp.route("/<record_id>", methods=["GET"])
def get_route(record_id: str):
    return get_by_id(record_id)


@events_bp.route("/<record_id>", methods=["PUT", "PATCH"])
def update_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(record_id, validated)


@events_bp.route("/<record_id>", methods=["DELETE"])
def delete_route(record_id: str):
    return delete(record_id)
