from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict
from urllib import parse, request


class StravaOAuthError(Exception):
    """Raised when Strava OAuth flow fails."""


class StravaOAuthService:
    AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"
    ATHLETE_URL = "https://www.strava.com/api/v3/athlete"
    ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
    ACTIVITY_DETAIL_URL = "https://www.strava.com/api/v3/activities/{}"

    def __init__(self):
        self.client_id = os.getenv("STRAVA_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("STRAVA_CLIENT_SECRET", "").strip()
        self.redirect_uri = os.getenv("STRAVA_REDIRECT_URI", "").strip()
        self.default_scopes = os.getenv("STRAVA_OAUTH_SCOPES", "read,activity:read_all").strip()
        self.state_secret = os.getenv("STRAVA_STATE_SECRET", "change-me").encode("utf-8")

    def _require_config(self):
        missing = []
        if not self.client_id:
            missing.append("STRAVA_CLIENT_ID")
        if not self.client_secret:
            missing.append("STRAVA_CLIENT_SECRET")
        if not self.redirect_uri:
            missing.append("STRAVA_REDIRECT_URI")
        if missing:
            raise StravaOAuthError("Missing required env vars: " + ", ".join(missing))

    def _build_signed_state(
        self,
        user_id: str | None = None,
        state_type: str = "link",
        ttl_sec: int = 600,
    ) -> str:
        payload: dict = {
            "type": state_type,
            "exp": int(time.time()) + ttl_sec,
        }
        if user_id is not None:
            payload["user_id"] = str(user_id)
        payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_json).decode("utf-8").rstrip("=")
        signature = hmac.new(self.state_secret, payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload_b64}.{signature}"

    def validate_state(self, state: str) -> dict:
        """Return ``{"type": str, "user_id": str | None}``."""
        if not state or "." not in state:
            raise StravaOAuthError("Invalid OAuth state")

        payload_b64, given_sig = state.split(".", 1)
        expected_sig = hmac.new(
            self.state_secret,
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(given_sig, expected_sig):
            raise StravaOAuthError("Invalid OAuth state signature")

        padding = "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8")
        payload = json.loads(payload_json)

        if int(payload.get("exp", 0)) < int(time.time()):
            raise StravaOAuthError("OAuth state expired")

        state_type = payload.get("type", "link")
        user_id = payload.get("user_id")
        if state_type == "link" and not user_id:
            raise StravaOAuthError("OAuth state missing user id")
        return {"type": state_type, "user_id": user_id}

    def build_authorize_url(self, user_id: str | None = None, state_type: str = "link") -> str:
        self._require_config()
        state = self._build_signed_state(user_id=user_id, state_type=state_type)
        query = parse.urlencode(
            {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                "approval_prompt": "auto",
                "scope": self.default_scopes,
                "state": state,
            }
        )
        return f"{self.AUTHORIZE_URL}?{query}"

    def exchange_code(self, code: str) -> Dict[str, Any]:
        self._require_config()
        if not code:
            raise StravaOAuthError("Missing OAuth code")

        body = parse.urlencode(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
            }
        ).encode("utf-8")
        req = request.Request(self.TOKEN_URL, data=body, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise StravaOAuthError(f"Failed to exchange Strava code: {exc}") from exc

        if not payload.get("access_token"):
            raise StravaOAuthError("Strava token response missing access_token")
        return payload

    def fetch_athlete(self, access_token: str) -> Dict[str, Any]:
        if not access_token:
            raise StravaOAuthError("Missing access token")

        req = request.Request(self.ATHLETE_URL, method="GET")
        req.add_header("Authorization", f"Bearer {access_token}")
        req.add_header("Accept", "application/json")

        try:
            with request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise StravaOAuthError(f"Failed to fetch Strava athlete profile: {exc}") from exc

        if not payload.get("id"):
            raise StravaOAuthError("Strava athlete payload missing id")
        return payload

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        self._require_config()
        if not refresh_token:
            raise StravaOAuthError("Missing refresh token")

        body = parse.urlencode(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }
        ).encode("utf-8")
        req = request.Request(self.TOKEN_URL, data=body, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise StravaOAuthError(f"Failed to refresh Strava token: {exc}") from exc

        if not payload.get("access_token"):
            raise StravaOAuthError("Strava token refresh response missing access_token")
        return payload

    def fetch_activities(
        self,
        access_token: str,
        *,
        before: int | None = None,
        after: int | None = None,
        page: int = 1,
        per_page: int = 30,
    ) -> list[Dict[str, Any]]:
        if not access_token:
            raise StravaOAuthError("Missing access token")
        if page < 1:
            raise StravaOAuthError("page must be >= 1")
        if per_page < 1 or per_page > 200:
            raise StravaOAuthError("per_page must be between 1 and 200")

        query: Dict[str, Any] = {"page": page, "per_page": per_page}
        if before is not None:
            query["before"] = int(before)
        if after is not None:
            query["after"] = int(after)

        url = f"{self.ACTIVITIES_URL}?{parse.urlencode(query)}"
        req = request.Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {access_token}")
        req.add_header("Accept", "application/json")

        try:
            with request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise StravaOAuthError(f"Failed to fetch Strava activities: {exc}") from exc

        if not isinstance(payload, list):
            raise StravaOAuthError("Unexpected Strava activities response format")
        return payload

    def fetch_activity_detail(self, access_token: str, activity_id: str) -> Dict[str, Any]:
        if not access_token:
            raise StravaOAuthError("Missing access token")

        url = self.ACTIVITY_DETAIL_URL.format(activity_id)
        req = request.Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {access_token}")
        req.add_header("Accept", "application/json")

        try:
            with request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise StravaOAuthError(f"Failed to fetch Strava activity detail: {exc}") from exc
