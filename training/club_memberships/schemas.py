from marshmallow import fields, validate
from marshmallow_sqlalchemy import SQLAlchemySchema
from .models import ClubMembership

class ClubMembershipSchema(SQLAlchemySchema):
    """
    Marshmallow schema for ClubMembership.
    """

    class Meta:
        model = ClubMembership
        load_instance = False

    membership_id = fields.UUID(dump_only=True)
    club_id = fields.UUID(required=True)
    user_id = fields.UUID(required=True)
    role = fields.String(validate=validate.OneOf(['member', 'club_admin']), required=True)
    status = fields.String(validate=validate.OneOf(['pending', 'approved', 'rejected']), required=True)
    joined_at = fields.DateTime()
