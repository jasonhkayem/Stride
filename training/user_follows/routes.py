from __future__ import annotations

from flask import Blueprint, request
from marshmallow import ValidationError

from .controller import create, delete, get_by_id, list_all, list_followers, list_following
from .schemas import UserFollowSchema


user_follows_bp = Blueprint("user_follows", __name__, url_prefix="/user_follows")

create_schema = UserFollowSchema()


@user_follows_bp.route("", methods=["POST"])
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@user_follows_bp.route("", methods=["GET"])
def list_route():
    return list_all()


@user_follows_bp.route("/<record_id>", methods=["GET"])
def get_route(record_id: str):
    return get_by_id(record_id)


@user_follows_bp.route("/followers/<user_id>", methods=["GET"])
def list_followers_route(user_id: str):
    return list_followers(user_id)


@user_follows_bp.route("/following/<user_id>", methods=["GET"])
def list_following_route(user_id: str):
    return list_following(user_id)


@user_follows_bp.route("/<record_id>", methods=["DELETE"])
def delete_route(record_id: str):
    return delete(record_id)
