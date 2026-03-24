from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema

from .models import ChatbotSessionMessage


class ChatbotSessionMessageSchema(SQLAlchemySchema):
    class Meta:
        model = ChatbotSessionMessage
        load_instance = False

    message_id = fields.UUID(dump_only=True)
    chatbot_id = fields.UUID(required=True)
    sender = fields.String(validate=validate.OneOf(["user", "assistant", "system"]), required=True)
    content = fields.String(required=True)
    created_at = fields.DateTime(dump_only=True)
