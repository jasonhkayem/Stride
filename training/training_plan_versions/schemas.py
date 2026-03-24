from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import TrainingPlanVersion


class TrainingPlanVersionSchema(SQLAlchemySchema):
    """
    Marshmallow schema for TrainingPlanVersion.
    """

    class Meta:
        model = TrainingPlanVersion
        load_instance = False

    version_id = fields.UUID(dump_only=True)
    user_plan_id = fields.UUID(required=True)
    version_number = fields.Integer(allow_none=True, load_default=None)
    plan_snapshot = fields.Dict(required=True)
    created_by = fields.String(validate=validate.OneOf(['ai', 'system']), required=True)
    change_summary = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
