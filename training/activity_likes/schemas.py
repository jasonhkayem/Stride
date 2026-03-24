from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import ActivityLike

class ActivityLikeSchema(SQLAlchemySchema):
    """
    Marshmallow schema for ActivityLike.
    """

    class Meta:
        model = ActivityLike
        load_instance = False

    like_id = fields.UUID(dump_only=True)
    activity_id = fields.UUID(required=True)
    user_id = fields.UUID(required=True)
    created_at = fields.DateTime(dump_only=True)
