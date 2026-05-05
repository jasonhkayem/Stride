from __future__ import annotations

from functools import wraps

from flask import g, jsonify, request

from .jwt_utils import JWTError, decode_token


def require_auth(f):
    """Verify the Bearer token in the Authorization header.

    On success, sets:
      g.current_user_id  – str UUID of the authenticated user
      g.current_role     – platform_role string from the token
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "authorization required"}), 401
        token = auth_header[7:]
        try:
            payload = decode_token(token)
        except JWTError as exc:
            return jsonify({"error": str(exc)}), 401
        g.current_user_id = payload["user_id"]
        g.current_role = payload.get("role", "user")
        return f(*args, **kwargs)

    return decorated
