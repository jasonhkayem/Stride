from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemySchema

from .models import UserFollow


class UserFollowSchema(SQLAlchemySchema):
    """
    Marshmallow schema for UserFollow.
    """

    class Meta:
        model = UserFollow
        load_instance = False

    follow_id = fields.UUID(dump_only=True)
    follower_id = fields.UUID(required=True)
    following_id = fields.UUID(required=True)
    created_at = fields.DateTime(dump_only=True)
