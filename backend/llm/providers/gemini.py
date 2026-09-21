"""
CORTEX LLM — Google Gemini provider (direct free-tier and paid).

Uses GEMINI_API_KEY or GOOGLE_API_KEY.
Key is sent via the x-goog-api-key request header — NOT embedded in the URL
(URL-embedded keys appear in proxy/access logs).

Free tier: subject to Google's rate limits.
Content submitted on free tier may be used by Google to improve its models.
For production/sensitive data use a paid Google Cloud project.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Optional

from backend.llm.errors import (
    AuthenticationError,
    LLMError,
    MalformedResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    QuotaExhaustedError,
    RateLimitedError,
    classify_http_error,
)
from backend.llm.providers.base import BaseLLMProvider
from backend.llm.telemetry import LLMResponse

logger = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(BaseLLMProvider):
    name = "gemini"
    is_paid = False  # Free tier available; paid tiers exist

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", timeout: float = 30.0) -> None:
        if not api_key:
            raise ValueError("GeminiProvider requires a non-empty api_key")
        self._api_key = api_key
        self.model = model
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        model: Optional[str] = None,
    ) -> LLMResponse:
        active_model = model or self.model
        t0 = time.perf_counter()

        contents = []
        if system:
            contents.append({"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTION: {system}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood. I will follow these instructions."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        url = f"{_GEMINI_BASE}/{active_model}:generateContent"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                # Key in header — NOT in URL
                "x-goog-api-key": self._api_key,
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise MalformedResponseError("Provider returned invalid JSON", provider=self.name) from exc
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            raise classify_http_error(exc.code, body, self.name) from exc
        except TimeoutError as exc:
            raise ProviderTimeoutError(
                f"Gemini request timed out after {self.timeout}s", provider=self.name
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                f"Cannot reach Gemini: {exc}", provider=self.name
            ) from exc

        latency_ms = (time.perf_counter() - t0) * 1000

        try:
            candidates = data.get("candidates", [])
            if not candidates:
                raise MalformedResponseError(
                    "Gemini returned no candidates", provider=self.name
                )
            text = candidates[0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            input_tok = usage.get("promptTokenCount")
            output_tok = usage.get("candidatesTokenCount")
            total_tok = usage.get("totalTokenCount")
        except (KeyError, IndexError, TypeError) as exc:
            raise MalformedResponseError(
                f"Unexpected Gemini response structure: {exc}", provider=self.name
            ) from exc

        return LLMResponse(
            text=text,
            provider=self.name,
            model=active_model,
            latency_ms=latency_ms,
            input_tokens=input_tok,
            output_tokens=output_tok,
            total_tokens=total_tok,
            billed_cost_usd=None,  # Free tier — no billing metadata
            fallback_used=False,
        )

    def health_check(self) -> dict:
        """List models to verify connectivity without generating text (non-billable)."""
        try:
            url = f"{_GEMINI_BASE}?pageSize=5"
            req = urllib.request.Request(
                url,
                headers={"x-goog-api-key": self._api_key},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
            return {
                "status": "HEALTHY",
                "provider": self.name,
                "model": self.model,
                "available_models_sample": models[:5],
            }
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                return {"status": "UNAVAILABLE", "provider": self.name, "error_code": "AUTHENTICATION_ERROR"}
            if exc.code == 429:
                return {"status": "DEGRADED", "provider": self.name, "error_code": "RATE_LIMITED"}
            return {"status": "UNAVAILABLE", "provider": self.name, "error_code": f"HTTP_{exc.code}"}
        except Exception as exc:
            return {"status": "UNAVAILABLE", "provider": self.name, "error_code": "PROVIDER_UNAVAILABLE"}
