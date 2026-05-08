from __future__ import annotations

from flask import Blueprint, request
from marshmallow import ValidationError

from training.auth.decorators import require_auth

from .controller import create, create_reply, delete, get_by_id, list_all, list_by_activity, list_replies, update
from .schemas import ActivityCommentSchema


activity_comments_bp = Blueprint("activity_comments", __name__, url_prefix="/activity_comments")

create_schema = ActivityCommentSchema()
update_schema = ActivityCommentSchema(partial=True)
reply_schema = ActivityCommentSchema(exclude=("parent_comment_id",))


@activity_comments_bp.route("", methods=["POST"])
@require_auth
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@activity_comments_bp.route("", methods=["GET"])
def list_route():
    return list_all()


@activity_comments_bp.route("/activity/<activity_id>", methods=["GET"])
def list_by_activity_route(activity_id: str):
    return list_by_activity(activity_id)


@activity_comments_bp.route("/<record_id>", methods=["GET"])
def get_route(record_id: str):
    return get_by_id(record_id)


@activity_comments_bp.route("/<record_id>/replies", methods=["GET"])
def list_replies_route(record_id: str):
    return list_replies(record_id)


@activity_comments_bp.route("/<record_id>/replies", methods=["POST"])
@require_auth
def create_reply_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = reply_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create_reply(record_id, validated)


@activity_comments_bp.route("/<record_id>", methods=["PUT", "PATCH"])
@require_auth
def update_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(record_id, validated)


@activity_comments_bp.route("/<record_id>", methods=["DELETE"])
@require_auth
def delete_route(record_id: str):
    return delete(record_id)
