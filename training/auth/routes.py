from __future__ import annotations

from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields

from .controller import forgot_password, login, me, reset_password, signup, strava_start


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


class SignupSchema(Schema):
    name = fields.String(required=True)
    email = fields.Email(required=True)
    password = fields.String(required=True)
    platform_role = fields.String(load_default="user")


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True)


signup_schema = SignupSchema()
login_schema = LoginSchema()


@auth_bp.route("/signup", methods=["POST"])
def signup_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = signup_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return signup(validated)


@auth_bp.route("/login", methods=["POST"])
def login_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = login_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return login(validated)


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password_route():
    payload = request.get_json(silent=True) or {}
    return forgot_password(payload)


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password_route():
    payload = request.get_json(silent=True) or {}
    return reset_password(payload)


@auth_bp.route("/strava/start", methods=["GET"])
def strava_start_route():
    return strava_start()


@auth_bp.route("/me/<user_id>", methods=["GET"])
def me_route(user_id: str):
    return me(user_id)
