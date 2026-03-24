from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemySchema

from .models import CompletedActionLap


class CompletedActionLapSchema(SQLAlchemySchema):
    class Meta:
        model = CompletedActionLap
        load_instance = False

    id = fields.UUID(dump_only=True)
    completed_action_id = fields.UUID(required=True)
    lap_index = fields.Integer(required=True)
    distance_km = fields.Decimal(required=True, as_string=False)
    moving_time_min = fields.Decimal(required=True, as_string=False)
    avg_pace_sec_per_km = fields.Integer(required=True)
    avg_heart_rate = fields.Integer(allow_none=True)
    elevation_gain_m = fields.Integer(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
