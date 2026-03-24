from __future__ import annotations

from flask import Blueprint, request
from marshmallow import ValidationError

from .controller import create, delete, get_by_id, list_all, update
from .schemas import UserTrainingPlanSchema


user_training_plans_bp = Blueprint("user_training_plans", __name__, url_prefix="/user_training_plans")

create_schema = UserTrainingPlanSchema()
update_schema = UserTrainingPlanSchema(partial=True)


@user_training_plans_bp.route("", methods=["POST"])
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@user_training_plans_bp.route("", methods=["GET"])
def list_route():
    include_related = request.args.get("include_related", "false").lower() == "true"
    return list_all(include_related=include_related)


@user_training_plans_bp.route("/<record_id>", methods=["GET"])
def get_route(record_id: str):
    include_related = request.args.get("include_related", "false").lower() == "true"
    return get_by_id(record_id, include_related=include_related)


@user_training_plans_bp.route("/<record_id>/full", methods=["GET"])
def get_full_route(record_id: str):
    return get_by_id(record_id, include_related=True)


@user_training_plans_bp.route("/<record_id>", methods=["PUT", "PATCH"])
def update_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(record_id, validated)


@user_training_plans_bp.route("/<record_id>", methods=["DELETE"])
def delete_route(record_id: str):
    return delete(record_id)
