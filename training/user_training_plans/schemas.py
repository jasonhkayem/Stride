from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import UserTrainingPlan


class UserTrainingPlanSchema(SQLAlchemySchema):
    """
    Marshmallow schema for UserTrainingPlan.
    """

    class Meta:
        model = UserTrainingPlan
        load_instance = False

    user_plan_id = fields.UUID(dump_only=True)
    user_id = fields.UUID(required=True)
    template_id = fields.UUID(required=True)
    current_version_id = fields.UUID(allow_none=True, load_default=None)
    start_date = fields.Date(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
