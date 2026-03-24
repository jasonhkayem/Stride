from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import ActivityComment


class ActivityCommentSchema(SQLAlchemySchema):
    """
    Marshmallow schema for ActivityComment.
    """

    class Meta:
        model = ActivityComment
        load_instance = False

    comment_id = fields.UUID(dump_only=True)
    activity_id = fields.UUID(required=True)
    user_id = fields.UUID(required=True)
    parent_comment_id = fields.UUID(allow_none=True)
    content = fields.String(required=True)
    created_at = fields.DateTime(dump_only=True)
