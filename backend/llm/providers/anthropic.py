"""CORTEX LLM — Anthropic Claude provider."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Optional

from backend.llm.errors import (
    MalformedResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    classify_http_error,
)
from backend.llm.providers.base import BaseLLMProvider
from backend.llm.telemetry import LLMResponse

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMProvider):
    name = "anthropic"
    is_paid = True

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-haiku-latest",
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("AnthropicProvider requires a non-empty api_key")
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

        payload = {
            "model": active_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
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
                f"Anthropic request timed out after {self.timeout}s", provider=self.name
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                f"Cannot reach Anthropic: {exc}", provider=self.name
            ) from exc

        latency_ms = (time.perf_counter() - t0) * 1000

        try:
            text = data["content"][0]["text"]
            usage = data.get("usage", {})
            input_tok = usage.get("input_tokens")
            output_tok = usage.get("output_tokens")
            total_tok = (input_tok or 0) + (output_tok or 0) or None
        except (KeyError, IndexError, TypeError) as exc:
            raise MalformedResponseError(
                f"Unexpected Anthropic response: {exc}", provider=self.name
            ) from exc

        return LLMResponse(
            text=text,
            provider=self.name,
            model=active_model,
            latency_ms=latency_ms,
            input_tokens=input_tok,
            output_tokens=output_tok,
            total_tokens=total_tok,
            fallback_used=False,
        )

    def health_check(self) -> dict:
        # Anthropic has no free metadata endpoint; return unknown
        return {"status": "UNKNOWN", "provider": self.name, "model": self.model}
