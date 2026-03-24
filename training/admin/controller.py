from __future__ import annotations

from datetime import date
from typing import Optional

from flask import jsonify

from .service import AdminAuthError, AdminDashboardService


service = AdminDashboardService()


def overview(admin_user_id: str, days: int):
    try:
        return jsonify(service.overview(admin_user_id=admin_user_id, days=days)), 200
    except AdminAuthError as exc:
        return jsonify({"error": str(exc)}), 403
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def trends(admin_user_id: str, days: int):
    try:
        return jsonify(service.trends(admin_user_id=admin_user_id, days=days)), 200
    except AdminAuthError as exc:
        return jsonify({"error": str(exc)}), 403
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def top_users(admin_user_id: str, limit: int):
    try:
        return jsonify(service.top_users(admin_user_id=admin_user_id, limit=limit)), 200
    except AdminAuthError as exc:
        return jsonify({"error": str(exc)}), 403
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500


def users(admin_user_id: str, page: int, page_size: int, search: Optional[str], from_date: Optional[date], to_date: Optional[date]):
    try:
        return (
            jsonify(
                service.users_monitoring(
                    admin_user_id=admin_user_id,
                    page=page,
                    page_size=page_size,
                    search=search,
                    from_date=from_date,
                    to_date=to_date,
                )
            ),
            200,
        )
    except AdminAuthError as exc:
        return jsonify({"error": str(exc)}), 403
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": "internal_server_error", "detail": str(exc)}), 500
