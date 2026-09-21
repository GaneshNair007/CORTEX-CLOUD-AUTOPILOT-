"""CORTEX LLM — Local Ollama provider (no network cost, no API key)."""

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
)
from backend.llm.providers.base import BaseLLMProvider
from backend.llm.telemetry import LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    name = "ollama"
    is_paid = False

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        timeout: float = 60.0,
    ) -> None:
        self.host = host.rstrip("/")
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
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            payload["system"] = system

        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read())
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                f"Cannot reach Ollama at {self.host} — is it running? ({exc})",
                provider=self.name,
            ) from exc
        except TimeoutError as exc:
            raise ProviderTimeoutError(
                f"Ollama request timed out after {self.timeout}s", provider=self.name
            ) from exc

        latency_ms = (time.perf_counter() - t0) * 1000

        text = body.get("response", "")
        eval_count = body.get("eval_count")
        eval_ns = body.get("eval_duration")
        prompt_eval = body.get("prompt_eval_count")

        return LLMResponse(
            text=text,
            provider=self.name,
            model=active_model,
            latency_ms=latency_ms,
            input_tokens=prompt_eval,
            output_tokens=eval_count,
            total_tokens=(prompt_eval or 0) + (eval_count or 0) or None,
            fallback_used=False,
        )

    def health_check(self) -> dict:
        try:
            req = urllib.request.Request(f"{self.host}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
            models = [m.get("name", "") for m in data.get("models", [])]
            model_available = any(self.model in m for m in models)
            return {
                "status": "HEALTHY" if model_available else "DEGRADED",
                "provider": self.name,
                "model": self.model,
                "model_available": model_available,
                "available_models": models[:10],
            }
        except Exception:
            return {"status": "UNAVAILABLE", "provider": self.name, "error_code": "PROVIDER_UNAVAILABLE"}
