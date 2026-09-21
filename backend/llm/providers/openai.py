"""
CORTEX LLM — OpenAI provider (direct OpenAI Platform, NOT CheaperInference).

Uses OPENAI_API_KEY with https://api.openai.com/v1 as the base URL.
If OPENAI_BASE_URL points to cheaperinference.com, use CheaperInferenceProvider instead.
"""

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


class OpenAIProvider(BaseLLMProvider):
    name = "openai"
    is_paid = True
    extra_payload: dict = {}

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAIProvider requires a non-empty api_key")
        self._api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
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

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": active_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            **self.extra_payload,
        }

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
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
                f"OpenAI request timed out after {self.timeout}s", provider=self.name
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                "Provider connection unavailable", provider=self.name
            ) from exc

        latency_ms = (time.perf_counter() - t0) * 1000

        try:
            text = data["choices"][0]["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                raise MalformedResponseError("Provider returned no final answer", provider=self.name)
            # Only final content is retained; reasoning_content and hidden traces
            # are deliberately excluded from all application response models.
            from backend.llm.sanitizer import sanitize
            text, _ = sanitize(text)
            usage = data.get("usage", {})
            input_tok = usage.get("prompt_tokens")
            output_tok = usage.get("completion_tokens")
            total_tok = usage.get("total_tokens")
            request_id = data.get("id")
        except (KeyError, IndexError, TypeError) as exc:
            raise MalformedResponseError(
                f"Unexpected OpenAI response: {exc}", provider=self.name
            ) from exc

        return LLMResponse(
            text=text,
            provider=self.name,
            model=active_model,
            latency_ms=latency_ms,
            input_tokens=input_tok,
            output_tokens=output_tok,
            total_tokens=total_tok,
            request_id=request_id,
            fallback_used=False,
        )

    def health_check(self) -> dict:
        try:
            req = urllib.request.Request(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            models = [m.get("id", "") for m in data.get("data", [])]
            return {
                "status": "HEALTHY",
                "provider": self.name,
                "model": self.model,
                "model_available": self.model in models,
            }
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                return {"status": "UNAVAILABLE", "provider": self.name, "error_code": "AUTHENTICATION_ERROR"}
            return {"status": "UNAVAILABLE", "provider": self.name, "error_code": f"HTTP_{exc.code}"}
        except Exception:
            return {"status": "UNAVAILABLE", "provider": self.name, "error_code": "PROVIDER_UNAVAILABLE"}
