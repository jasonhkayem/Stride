from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import ChatbotSession

class ChatbotSessionSchema(SQLAlchemySchema):
    """
    Marshmallow schema for ChatbotSession.
    """

    class Meta:
        model = ChatbotSession
        load_instance = False

    chatbot_id = fields.UUID(dump_only=True)
    user_id = fields.UUID(required=True)
    session_type = fields.String(required=True)
    related_completed_action_id = fields.UUID(allow_none=True)
    related_activity_id = fields.UUID(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    closed_at = fields.DateTime()
