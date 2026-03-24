from __future__ import annotations

from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields, validate

from .controller import (
    create,
    delete,
    get_by_id,
    list_all,
    list_messages,
    reply,
    suggest_training_plan_actions,
    update,
)
from .schemas import ChatbotSessionSchema


chatbot_sessions_bp = Blueprint("chatbot_sessions", __name__, url_prefix="/chatbot_sessions")

create_schema = ChatbotSessionSchema()
update_schema = ChatbotSessionSchema(partial=True)


class ChatbotReplySchema(Schema):
    user_message = fields.String(required=True)
    system_prompt = fields.String(required=False, allow_none=True)
    max_context_messages = fields.Integer(
        required=False,
        load_default=20,
        validate=validate.Range(min=1, max=100),
    )


reply_schema = ChatbotReplySchema()


class TrainingPlanSuggestionSchema(Schema):
    version_id = fields.UUID(required=True)
    user_prompt = fields.String(required=True)
    apply_actions = fields.Boolean(required=False, load_default=False)


training_plan_suggestion_schema = TrainingPlanSuggestionSchema()


@chatbot_sessions_bp.route("", methods=["POST"])
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@chatbot_sessions_bp.route("", methods=["GET"])
def list_route():
    return list_all()


@chatbot_sessions_bp.route("/<record_id>", methods=["GET"])
def get_route(record_id: str):
    return get_by_id(record_id)


@chatbot_sessions_bp.route("/<record_id>", methods=["PUT", "PATCH"])
def update_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(record_id, validated)


@chatbot_sessions_bp.route("/<record_id>", methods=["DELETE"])
def delete_route(record_id: str):
    return delete(record_id)


@chatbot_sessions_bp.route("/<record_id>/reply", methods=["POST"])
def reply_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = reply_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return reply(record_id, validated)


@chatbot_sessions_bp.route("/<record_id>/messages", methods=["GET"])
def list_messages_route(record_id: str):
    limit_raw = request.args.get("limit", "50")
    try:
        limit = int(limit_raw)
    except ValueError:
        return {"errors": {"limit": ["Not a valid integer."]}}, 400
    if limit < 1 or limit > 200:
        return {"errors": {"limit": ["Must be between 1 and 200."]}}, 400
    return list_messages(record_id, limit=limit)


@chatbot_sessions_bp.route("/<record_id>/suggest_training_plan_actions", methods=["POST"])
def suggest_training_plan_actions_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = training_plan_suggestion_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return suggest_training_plan_actions(record_id, validated)
