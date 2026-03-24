from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema

from .models import TrainingPlanAdjustment


class TrainingPlanAdjustmentSchema(SQLAlchemySchema):
    class Meta:
        model = TrainingPlanAdjustment
        load_instance = False

    adjustment_id = fields.UUID(dump_only=True)
    user_training_plan_id = fields.UUID(required=True)
    session_id = fields.UUID(required=True)
    previous_version_id = fields.UUID(required=True)
    new_version_id = fields.UUID(allow_none=True)
    suggested_changes = fields.Dict(required=True)
    validated_changes = fields.Dict(allow_none=True)
    status = fields.String(
        validate=validate.OneOf(["suggested", "approved", "rejected", "applied"]),
        load_default="suggested",
    )
    created_at = fields.DateTime(dump_only=True)
