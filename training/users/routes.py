from __future__ import annotations

from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields

from training.auth.decorators import require_auth

from .controller import (
    create,
    delete,
    get_by_id,
    list_all,
    search_by_username,
    strava_authorize,
    strava_connect_callback,
    strava_connect,
    strava_disconnect,
    strava_status,
    update,
    upload_avatar,
)
from .schemas import UserSchema


users_bp = Blueprint("users", __name__, url_prefix="/users")

create_schema = UserSchema()
update_schema = UserSchema(partial=True)


class StravaConnectSchema(Schema):
    code = fields.String(required=True)
    state = fields.String(required=True)


strava_connect_schema = StravaConnectSchema()


@users_bp.route("", methods=["POST"])
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@users_bp.route("", methods=["GET"])
def list_route():
    username_query = request.args.get("username")
    if username_query is not None:
        limit_raw = request.args.get("limit", "10")
        try:
            limit = int(limit_raw)
        except (TypeError, ValueError):
            limit = 10
        return search_by_username(query=username_query, limit=limit)
    include_related = request.args.get("include_related", "false").lower() == "true"
    return list_all(include_related=include_related)


@users_bp.route("/<record_id>", methods=["GET"])
def get_route(record_id: str):
    include_related = request.args.get("include_related", "false").lower() == "true"
    return get_by_id(record_id, include_related=include_related)


@users_bp.route("/<record_id>/full", methods=["GET"])
def get_full_route(record_id: str):
    return get_by_id(record_id, include_related=True)


@users_bp.route("/<record_id>", methods=["PUT", "PATCH"])
@require_auth
def update_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(record_id, validated)


@users_bp.route("/<record_id>", methods=["DELETE"])
@require_auth
def delete_route(record_id: str):
    return delete(record_id)


@users_bp.route("/<record_id>/avatar", methods=["POST"])
@require_auth
def upload_avatar_route(record_id: str):
    return upload_avatar(record_id)


@users_bp.route("/<record_id>/strava/oauth/start", methods=["GET"])
@require_auth
def strava_authorize_route(record_id: str):
    return strava_authorize(record_id)


@users_bp.route("/<record_id>/strava/oauth/callback", methods=["POST"])
@require_auth
def strava_connect_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = strava_connect_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return strava_connect(record_id, validated)


@users_bp.route("/strava/oauth/callback", methods=["GET", "POST"])
def strava_generic_callback_route():
    if request.method == "GET":
        payload = {
            "code": request.args.get("code"),
            "state": request.args.get("state"),
        }
    else:
        payload = request.get_json(silent=True) or {}

    try:
        validated = strava_connect_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return strava_connect_callback(validated)


@users_bp.route("/<record_id>/strava", methods=["GET"])
@require_auth
def strava_status_route(record_id: str):
    return strava_status(record_id)


@users_bp.route("/<record_id>/strava", methods=["DELETE"])
@require_auth
def strava_disconnect_route(record_id: str):
    return strava_disconnect(record_id)
