from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import Activity

class ActivitySchema(SQLAlchemySchema):
    """
    Marshmallow schema for Activity.
    """

    class Meta:
        model = Activity
        load_instance = False

    activity_id = fields.UUID(dump_only=True)
    user_id = fields.UUID(required=True)
    strava_id = fields.String()
    activity_type = fields.String(validate=validate.OneOf(['run', 'bike', 'swim', 'walk', 'hike', 'weights', 'mobility', 'yoga', 'other']), required=True)
    distance = fields.Float(load_default=0.0)
    duration = fields.Integer(required=True)
    timestamp = fields.DateTime(required=True)
    route_polyline = fields.String(allow_none=True, load_default=None)
    average_heart_rate = fields.Float(allow_none=True, load_default=None)
    laps = fields.List(fields.Dict(), allow_none=True, load_default=None)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
