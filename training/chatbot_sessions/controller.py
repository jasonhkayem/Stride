from __future__ import annotations

from typing import Any, Dict

from flask import jsonify

from training.chatbot_session_messages.schemas import ChatbotSessionMessageSchema
from training.common.crud_service import NotFoundError
from training.services.llm_service import LLMServiceError

from .schemas import ChatbotSessionSchema
from .service import ChatbotSessionService


service = ChatbotSessionService()
schema = ChatbotSessionSchema()
message_schema = ChatbotSessionMessageSchema()


def create(payload: Dict[str, Any]):
    try:
        item = service.create(payload)
        return jsonify(schema.dump(item)), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def get_by_id(record_id: str):
    try:
        item = service.get_by_id(record_id)
        if item is None:
            return jsonify({"error": "record not found"}), 404
        return jsonify(schema.dump(item)), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def list_all():
    try:
        items = service.list_all()
        return jsonify(schema.dump(items, many=True)), 200
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def update(record_id: str, payload: Dict[str, Any]):
    try:
        item = service.update(record_id, payload)
        return jsonify(schema.dump(item)), 200
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def delete(record_id: str):
    try:
        service.delete(record_id)
        return jsonify({"status": "deleted"}), 200
    except NotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def reply(record_id: str, payload: Dict[str, Any], caller_user_id: str = ""):
    try:
        # Ownership check — session must belong to the authenticated user
        if caller_user_id:
            session_obj = service.get_by_id(record_id)
            if session_obj is None:
                return jsonify({"error": "session not found"}), 404
            if str(session_obj.user_id) != caller_user_id:
                return jsonify({"error": "forbidden"}), 403

        result = service.generate_reply(
            chatbot_id=record_id,
            user_message=payload.get("user_message", ""),
            max_context_messages=payload.get("max_context_messages", 20),
        )
        return jsonify(result), 200
    except LLMServiceError as exc:
        return jsonify({"error": str(exc)}), 502
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message else 400
        return jsonify({"error": message}), status
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def list_messages(record_id: str, limit: int = 50):
    try:
        items = service.list_messages(record_id, limit=limit)
        return jsonify(message_schema.dump(items, many=True)), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def suggest_training_plan_actions(record_id: str, payload: Dict[str, Any]):
    try:
        result = service.suggest_training_plan_actions(
            chatbot_id=record_id,
            version_id=str(payload.get("version_id")),
            user_prompt=payload.get("user_prompt", ""),
            apply_actions=bool(payload.get("apply_actions", False)),
        )
        status_code = 201 if result.get("applied") else 200
        return jsonify(result), status_code
    except LLMServiceError as exc:
        return jsonify({"error": str(exc)}), 502
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message else 400
        return jsonify({"error": message}), status
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500
