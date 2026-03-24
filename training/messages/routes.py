from __future__ import annotations

from flask import Blueprint, request
from marshmallow import ValidationError

from .controller import create, delete, get_by_id, list_all, update
from .schemas import MessageSchema


messages_bp = Blueprint("messages", __name__, url_prefix="/messages")

create_schema = MessageSchema()
update_schema = MessageSchema(partial=True)


@messages_bp.route("", methods=["POST"])
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@messages_bp.route("", methods=["GET"])
def list_route():
    return list_all()


@messages_bp.route("/<record_id>", methods=["GET"])
def get_route(record_id: str):
    return get_by_id(record_id)


@messages_bp.route("/<record_id>", methods=["PUT", "PATCH"])
def update_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(record_id, validated)


@messages_bp.route("/<record_id>", methods=["DELETE"])
def delete_route(record_id: str):
    return delete(record_id)
