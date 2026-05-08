from __future__ import annotations

import uuid

from flask import Blueprint, g, jsonify, request
from sqlalchemy import select

from training.auth.decorators import require_auth
from training.db import SessionLocal

from .models import CompletedPlanSession


completed_plan_sessions_bp = Blueprint(
    "completed_plan_sessions", __name__, url_prefix="/completed_plan_sessions"
)


def _serialize(r: CompletedPlanSession) -> dict:
    return {
        "id": str(r.id),
        "user_id": str(r.user_id),
        "version_id": str(r.version_id),
        "week_index": r.week_index,
        "session_index": r.session_index,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
    }


@completed_plan_sessions_bp.route("", methods=["GET"])
@require_auth
def list_route():
    version_id_str = request.args.get("version_id")
    if not version_id_str:
        return jsonify({"error": "version_id is required"}), 400
    try:
        version_id = uuid.UUID(version_id_str)
    except ValueError:
        return jsonify({"error": "invalid version_id"}), 400

    user_id = uuid.UUID(g.current_user_id)
    with SessionLocal() as session:
        rows = list(
            session.execute(
                select(CompletedPlanSession).where(
                    CompletedPlanSession.user_id == user_id,
                    CompletedPlanSession.version_id == version_id,
                )
            ).scalars().all()
        )
    return jsonify([_serialize(r) for r in rows])


@completed_plan_sessions_bp.route("", methods=["POST"])
@require_auth
def create_route():
    payload = request.get_json(silent=True) or {}
    try:
        version_id = uuid.UUID(str(payload["version_id"]))
        week_index = int(payload["week_index"])
        session_index = int(payload["session_index"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "version_id, week_index, and session_index are required"}), 400

    user_id = uuid.UUID(g.current_user_id)
    with SessionLocal() as session:
        existing = session.execute(
            select(CompletedPlanSession).where(
                CompletedPlanSession.user_id == user_id,
                CompletedPlanSession.version_id == version_id,
                CompletedPlanSession.week_index == week_index,
                CompletedPlanSession.session_index == session_index,
            )
        ).scalar_one_or_none()
        if existing:
            return jsonify(_serialize(existing)), 200

        record = CompletedPlanSession(
            user_id=user_id,
            version_id=version_id,
            week_index=week_index,
            session_index=session_index,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return jsonify(_serialize(record)), 201


@completed_plan_sessions_bp.route("/<record_id>", methods=["DELETE"])
@require_auth
def delete_route(record_id: str):
    try:
        pk = uuid.UUID(record_id)
    except ValueError:
        return jsonify({"error": "invalid id"}), 400

    user_id = uuid.UUID(g.current_user_id)
    with SessionLocal() as session:
        record = session.execute(
            select(CompletedPlanSession).where(
                CompletedPlanSession.id == pk,
                CompletedPlanSession.user_id == user_id,
            )
        ).scalar_one_or_none()
        if record is None:
            return jsonify({"error": "not found"}), 404
        session.delete(record)
        session.commit()
    return jsonify({"deleted": True})
