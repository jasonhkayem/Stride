from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, request

from .controller import kick_logs, overview, top_users, trends, users


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _admin_header() -> str:
    return (request.headers.get("X-Admin-User-Id") or "").strip()


def _int_param(name: str, default: int) -> int:
    raw = request.args.get(name, str(default)).strip()
    return int(raw)


def _date_param(name: str):
    raw = (request.args.get(name) or "").strip()
    if not raw:
        return None
    return date.fromisoformat(raw)


@admin_bp.route("/overview", methods=["GET"])
def overview_route():
    try:
        days = _int_param("days", 30)
    except ValueError:
        return jsonify({"error": "days must be an integer"}), 400
    return overview(admin_user_id=_admin_header(), days=days)


@admin_bp.route("/trends", methods=["GET"])
def trends_route():
    try:
        days = _int_param("days", 30)
    except ValueError:
        return jsonify({"error": "days must be an integer"}), 400
    return trends(admin_user_id=_admin_header(), days=days)


@admin_bp.route("/top_users", methods=["GET"])
def top_users_route():
    try:
        limit = _int_param("limit", 10)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400
    return top_users(admin_user_id=_admin_header(), limit=limit)


@admin_bp.route("/kick_logs", methods=["GET"])
def kick_logs_route():
    try:
        limit = _int_param("limit", 50)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400
    return kick_logs(admin_user_id=_admin_header(), limit=limit)


@admin_bp.route("/users", methods=["GET"])
def users_route():
    try:
        page = _int_param("page", 1)
        page_size = _int_param("page_size", 20)
    except ValueError:
        return jsonify({"error": "page and page_size must be integers"}), 400
    search = (request.args.get("search") or "").strip() or None
    try:
        from_date = _date_param("from_date")
        to_date = _date_param("to_date")
    except ValueError:
        return jsonify({"error": "from_date and to_date must use YYYY-MM-DD"}), 400
    return users(
        admin_user_id=_admin_header(),
        page=page,
        page_size=page_size,
        search=search,
        from_date=from_date,
        to_date=to_date,
    )
