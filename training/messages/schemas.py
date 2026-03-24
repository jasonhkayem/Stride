from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import Message

class MessageSchema(SQLAlchemySchema):
    """
    Marshmallow schema for Message.
    """

    class Meta:
        model = Message
        load_instance = False

    message_id = fields.UUID(dump_only=True)
    chat_id = fields.UUID(required=True)
    sender = fields.String(validate=validate.OneOf(['user', 'ai']), required=True)
    content = fields.String(required=True)
    message_type = fields.String(validate=validate.OneOf(['reflection', 'chat', 'system']), required=True)
    created_at = fields.DateTime(dump_only=True)
