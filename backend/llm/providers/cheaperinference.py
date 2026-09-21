"""
CORTEX LLM — CheaperInference provider (first-class, not disguised as OpenAI).

CheaperInference is a wallet-backed, usage-based inference gateway.
It supports an OpenAI-compatible API format, but it is NOT OpenAI.
Telemetry correctly labels it as "cheaperinference", not "openai".

Billing:
  - Wallet-funded. Requires minimum $5 deposit (check current docs for bonus offers).
  - Each successful response may include billing metadata in the response body.
  - Provider attribution:
      gateway     = "cheaperinference"
      model       = the model served (e.g. gemini-2.0-flash)
      model_provider = inferred from model name (e.g. google)

Key scopes:
  - Runtime inference key: use "inference" scope only.
  - Usage/reporting key (optional): use "usage:read account:read" scope — separate key.

Docs: https://api.cheaperinference.com
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from decimal import Decimal
from functools import lru_cache
from typing import Optional

from backend.llm.errors import (
    AuthenticationError,
    InsufficientBalanceError,
    LLMError,
    MalformedResponseError,
    ModelUnavailableError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RateLimitedError,
    classify_http_error,
)
from backend.llm.providers.base import BaseLLMProvider
from backend.llm.telemetry import LLMResponse, _infer_model_provider

logger = logging.getLogger(__name__)


class CheaperInferenceProvider(BaseLLMProvider):
    name = "cheaperinference"
    is_paid = True  # Wallet-backed usage-based pricing

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        base_url: str = "https://api.cheaperinference.com/v1",
        timeout: float = 30.0,
        usage_api_key: Optional[str] = None,
    ) -> None:
        if not api_key:
            raise ValueError("CheaperInferenceProvider requires a non-empty api_key")
        self._api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._usage_api_key = usage_api_key

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
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            err = classify_http_error(exc.code, body, self.name)
            # Surface wallet-related errors explicitly
            if exc.code == 402 or "insufficient" in body.lower() or "balance" in body.lower():
                raise InsufficientBalanceError(
                    "CheaperInference wallet balance insufficient. Add funds to continue.",
                    provider=self.name,
                ) from exc
            raise err from exc
        except TimeoutError as exc:
            raise ProviderTimeoutError(
                f"CheaperInference timed out after {self.timeout}s", provider=self.name
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderUnavailableError(
                f"Cannot reach CheaperInference: {exc}", provider=self.name
            ) from exc

        latency_ms = (time.perf_counter() - t0) * 1000

        try:
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            input_tok = usage.get("prompt_tokens")
            output_tok = usage.get("completion_tokens")
            total_tok = usage.get("total_tokens")
        except (KeyError, IndexError, TypeError) as exc:
            raise MalformedResponseError(
                f"Unexpected CheaperInference response: {exc}", provider=self.name
            ) from exc

        # Parse CheaperInference billing metadata when available
        billed_cost: Optional[Decimal] = None
        request_id: Optional[str] = None
        ci_meta = data.get("cheaper_inference", {})
        if ci_meta:
            request_id = ci_meta.get("request_id")
            raw_cost = ci_meta.get("billed_cost_usd")
            if raw_cost is not None:
                try:
                    billed_cost = Decimal(str(raw_cost))
                except Exception:
                    logger.debug("Could not parse billed_cost_usd: %r", raw_cost)

        # Also check top-level id as request_id fallback
        if not request_id:
            request_id = data.get("id")

        return LLMResponse(
            text=text,
            provider=self.name,
            gateway=self.name,
            model=active_model,
            model_provider=_infer_model_provider(self.name, active_model),
            latency_ms=latency_ms,
            input_tokens=input_tok,
            output_tokens=output_tok,
            total_tokens=total_tok,
            billed_cost_usd=billed_cost,
            request_id=request_id,
            fallback_used=False,
        )

    def health_check(self) -> dict:
        """
        Check model availability via GET /v1/models (non-billable).
        Verifies the configured model is listed.
        """
        try:
            req = urllib.request.Request(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())

            models = [m.get("id", m.get("name", "")) for m in data.get("data", [])]
            model_available = self.model in models or not models  # assume available if list is empty

            status = "HEALTHY" if model_available else "DEGRADED"
            return {
                "status": status,
                "provider": self.name,
                "model": self.model,
                "model_available": model_available,
                "cost_type": "wallet-backed",
            }
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                return {"status": "UNAVAILABLE", "provider": self.name, "error_code": "AUTHENTICATION_ERROR"}
            return {"status": "UNAVAILABLE", "provider": self.name, "error_code": f"HTTP_{exc.code}"}
        except Exception:
            return {"status": "UNAVAILABLE", "provider": self.name, "error_code": "PROVIDER_UNAVAILABLE"}

    def get_balance(self) -> Optional[dict]:
        """
        Query wallet balance using the usage API key (account:read scope).
        Returns None if usage key is not configured.
        WARNING: Never expose this to unauthenticated API callers.
        """
        if not self._usage_api_key:
            return None
        try:
            req = urllib.request.Request(
                f"{self.base_url}/account/balance",
                headers={"Authorization": f"Bearer {self._usage_api_key}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            logger.debug("Balance check failed: %s", exc)
            return None
