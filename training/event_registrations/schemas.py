from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import EventRegistration

class EventRegistrationSchema(SQLAlchemySchema):
    """
    Marshmallow schema for EventRegistration.
    """

    class Meta:
        model = EventRegistration
        load_instance = False

    registration_id = fields.UUID(dump_only=True)
    event_id = fields.UUID(required=True)
    user_id = fields.UUID(required=True)
    registered_at = fields.DateTime(dump_only=True)
