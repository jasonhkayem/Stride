from __future__ import annotations

import json
import os
from typing import Any, Dict, List
from urllib import request


class LLMServiceError(Exception):
    """Raised when the LLM request fails or returns invalid data."""


class LLMService:
    """
    Minimal OpenAI-compatible chat client.
    Configure via env:
    - LLM_API_URL (default: OpenAI chat completions endpoint)
    - LLM_API_KEY
    - LLM_MODEL (default: gpt-4.1-mini)
    """

    def __init__(self):
        self.api_url = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions").strip()
        self.api_key = os.getenv("LLM_API_KEY", "").strip()
        self.model = os.getenv("LLM_MODEL", "gpt-4.1-mini").strip()
        self.timeout_sec = int(os.getenv("LLM_TIMEOUT_SEC", "90"))
        self.auth_scheme = os.getenv("LLM_AUTH_SCHEME", "Bearer").strip()

    def _require_config(self):
        if not self.api_key:
            raise LLMServiceError("Missing LLM_API_KEY")

    @staticmethod
    def _extract_text(payload: Dict[str, Any]) -> str:
        choices = payload.get("choices") or []
        if not choices:
            raise LLMServiceError("LLM response missing choices")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            return "".join(parts).strip()
        raise LLMServiceError("LLM response content format is unsupported")

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> str:
        self._require_config()

        body = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        ).encode("utf-8")

        req = request.Request(self.api_url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"{self.auth_scheme} {self.api_key}")

        try:
            with request.urlopen(req, timeout=self.timeout_sec) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise LLMServiceError(f"LLM API call failed: {exc}") from exc

        return self._extract_text(payload)
