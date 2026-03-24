from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemySchema

from training.completed_action_laps.schemas import CompletedActionLapSchema

from .models import CompletedAction


class CompletedActionSchema(SQLAlchemySchema):
    class Meta:
        model = CompletedAction
        load_instance = False

    id = fields.UUID(dump_only=True)
    training_plan_action_id = fields.UUID(required=True)
    user_id = fields.UUID(required=True)
    strava_activity_id = fields.Integer(allow_none=True)
    name = fields.String(required=True)
    action_type = fields.String(required=True)
    actual_distance_km = fields.Decimal(required=True, as_string=False)
    actual_duration_min = fields.Integer(required=True)
    avg_pace_sec_per_km = fields.Integer(required=True)
    avg_heart_rate = fields.Integer(allow_none=True)
    elevation_gain_m = fields.Integer(allow_none=True)
    calories = fields.Decimal(allow_none=True, as_string=False)
    gear_id = fields.String(allow_none=True)
    manual_entry = fields.Boolean(load_default=False)
    completed_at = fields.DateTime(required=True)
    route_polyline = fields.String(required=True)
    created_at = fields.DateTime(dump_only=True)
    laps = fields.List(fields.Nested(CompletedActionLapSchema(exclude=("completed_action_id",))), load_default=list)
