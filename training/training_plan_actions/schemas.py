from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import TrainingPlanAction

class TrainingPlanActionSchema(SQLAlchemySchema):
    """
    Marshmallow schema for TrainingPlanAction.
    """

    class Meta:
        model = TrainingPlanAction
        load_instance = False

    action_id = fields.UUID(dump_only=True)
    version_id = fields.UUID(required=True)
    action_type = fields.String(validate=validate.OneOf(['adjust_volume', 'adjust_intensity', 'insert_rest_day', 'reschedule_session']), required=True)
    parameters = fields.Dict(required=True)
    applied_at = fields.DateTime(dump_only=True)
