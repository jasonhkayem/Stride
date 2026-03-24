from __future__ import annotations

from flask import Blueprint, request
from marshmallow import Schema, ValidationError, fields

from .controller import approve, create, delete, get_by_id, list_all, list_by_club, reject, update
from .schemas import ClubMembershipSchema


club_memberships_bp = Blueprint("club_memberships", __name__, url_prefix="/club_memberships")

create_schema = ClubMembershipSchema()
update_schema = ClubMembershipSchema(partial=True)


class MembershipFilterSchema(Schema):
    club_id = fields.UUID(required=True)
    status = fields.String(required=False, allow_none=True)


filter_schema = MembershipFilterSchema()


@club_memberships_bp.route("", methods=["POST"])
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        validated = create_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return create(validated)


@club_memberships_bp.route("", methods=["GET"])
def list_route():
    club_id = request.args.get("club_id")
    status = request.args.get("status")
    if club_id:
        try:
            validated = filter_schema.load({"club_id": club_id, "status": status})
        except ValidationError as exc:
            return {"errors": exc.messages}, 400
        return list_by_club(str(validated["club_id"]), status=validated.get("status"))
    return list_all()


@club_memberships_bp.route("/<record_id>", methods=["GET"])
def get_route(record_id: str):
    return get_by_id(record_id)


@club_memberships_bp.route("/<record_id>/approve", methods=["POST"])
def approve_route(record_id: str):
    return approve(record_id)


@club_memberships_bp.route("/<record_id>/reject", methods=["POST"])
def reject_route(record_id: str):
    return reject(record_id)


@club_memberships_bp.route("/<record_id>", methods=["PUT", "PATCH"])
def update_route(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        validated = update_schema.load(payload)
    except ValidationError as exc:
        return {"errors": exc.messages}, 400
    return update(record_id, validated)


@club_memberships_bp.route("/<record_id>", methods=["DELETE"])
def delete_route(record_id: str):
    return delete(record_id)
