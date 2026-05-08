from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


_JWT_HEADER_B64 = (
    base64.urlsafe_b64encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    .rstrip(b"=")
    .decode()
)


class JWTError(Exception):
    """Raised when a JWT cannot be verified or decoded."""


_INSECURE_DEFAULT = "dev-jwt-secret-change-in-production"


def _secret() -> bytes:
    value = os.getenv("JWT_SECRET", _INSECURE_DEFAULT)
    if value == _INSECURE_DEFAULT:
        logger.warning(
            "JWT_SECRET is not set — using the insecure default. "
            "Set JWT_SECRET in your environment before deploying."
        )
    return value.encode("utf-8")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = 4 - len(s) % 4
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s)


def generate_token(
    user_id: str,
    platform_role: str,
    expires_in: int = 86400 * 30,  # 30 days
) -> str:
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "role": platform_role,
        "iat": now,
        "exp": now + expires_in,
    }
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{_JWT_HEADER_B64}.{payload_b64}"
    sig = hmac.new(_secret(), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(sig)}"


def decode_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT. Raises JWTError on any failure."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise JWTError("malformed token")

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"

        expected_sig = hmac.new(
            _secret(), signing_input.encode("utf-8"), hashlib.sha256
        ).digest()
        actual_sig = _b64url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            raise JWTError("invalid token signature")

        payload = json.loads(_b64url_decode(payload_b64))

        if payload.get("exp", 0) < int(time.time()):
            raise JWTError("token expired")

        return payload
    except JWTError:
        raise
    except Exception as exc:
        raise JWTError(f"token decode failed: {exc}") from exc
