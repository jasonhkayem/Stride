from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import TrainingPlanTemplate

class TrainingPlanTemplateSchema(SQLAlchemySchema):
    """
    Marshmallow schema for TrainingPlanTemplate.
    """

    class Meta:
        model = TrainingPlanTemplate
        load_instance = False

    template_id = fields.UUID(dump_only=True)
    goal_race = fields.String(required=True)
    duration_weeks = fields.Integer(required=True)
    structure = fields.Dict(required=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
