from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import User

class UserSchema(SQLAlchemySchema):
    """
    Marshmallow schema for User.
    """

    class Meta:
        model = User
        load_instance = False

    user_id = fields.UUID(dump_only=True)
    name = fields.String(required=True)
    email = fields.Email(required=True)
    password_hash = fields.String(required=True, load_only=True)
    platform_role = fields.String(validate=validate.OneOf(['user', 'super_admin']), required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    username = fields.String(dump_only=True)
    date_of_birth = fields.Date(dump_only=True)
    profile_picture_url = fields.String(dump_only=True)
    strava_athlete_id = fields.String(dump_only=True)
    strava_connected_at = fields.DateTime(dump_only=True)
    weekly_goal_km = fields.Float(allow_none=True, load_default=None)
