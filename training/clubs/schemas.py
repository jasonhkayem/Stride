from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import Club

class ClubSchema(SQLAlchemySchema):
    """
    Marshmallow schema for Club.
    """

    class Meta:
        model = Club
        load_instance = False

    club_id = fields.UUID(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, error="Club name cannot be empty."))
    description = fields.String()
    created_by = fields.UUID(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
