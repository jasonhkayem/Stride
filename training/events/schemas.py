from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import Event

class EventSchema(SQLAlchemySchema):
    """
    Marshmallow schema for Event.
    """

    class Meta:
        model = Event
        load_instance = False

    event_id = fields.UUID(dump_only=True)
    club_id = fields.UUID(required=True)
    created_by = fields.UUID(required=True, load_only=True)
    name = fields.String(required=True)
    description = fields.String()
    event_date = fields.Date(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
