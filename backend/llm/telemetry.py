"""
CORTEX LLM — Typed response model and per-incident call budget.

LLMResponse carries all observability fields.
LLMCallBudget enforces the per-incident LLM call limit to prevent runaway spend.
"""

from __future__ import annotations

import threading
import time
from decimal import Decimal
from typing import Optional


class LLMResponse:
    """
    Typed result returned by every LLMClient.generate() call.

    All fields the provider does not report are None — we never
    fabricate token counts or costs.
    """

    __slots__ = (
        "text",
        "provider",
        "gateway",
        "model",
        "model_provider",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "billed_cost_usd",
        "request_id",
        "fallback_used",
        "fallback_reason",
        "mode",
    )

    def __init__(
        self,
        *,
        text: str,
        provider: str,
        model: str,
        latency_ms: float,
        gateway: Optional[str] = None,
        model_provider: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        billed_cost_usd: Optional[Decimal] = None,
        request_id: Optional[str] = None,
        fallback_used: bool = False,
        fallback_reason: Optional[str] = None,
    ) -> None:
        self.text = text
        self.provider = provider
        self.gateway = gateway or provider
        self.model = model
        self.model_provider = model_provider or _infer_model_provider(provider, model)
        self.latency_ms = round(latency_ms, 2)
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens
        self.billed_cost_usd = billed_cost_usd
        self.request_id = request_id
        self.fallback_used = fallback_used
        self.fallback_reason = fallback_reason
        # Legacy compat: mode mirrors provider
        self.mode = provider

    def to_dict(self) -> dict:
        """Serializable dict — safe for API responses and telemetry."""
        return {
            "text": self.text,
            "provider": self.provider,
            "gateway": self.gateway,
            "model": self.model,
            "model_provider": self.model_provider,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "billed_cost_usd": str(self.billed_cost_usd) if self.billed_cost_usd is not None else None,
            "request_id": self.request_id,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            # Legacy fields expected by existing code
            "mode": self.provider,
            "eval_count": self.output_tokens,
        }

    # Let existing code that does res["text"] still work
    def __getitem__(self, key: str):
        return self.to_dict()[key]

    def get(self, key: str, default=None):
        return self.to_dict().get(key, default)


def _infer_model_provider(provider: str, model: str) -> str:
    """Best-effort inference of the underlying model provider family."""
    if provider == "nvidia":
        return "nvidia"
    if provider == "gemini":
        return "google"
    if provider == "anthropic":
        return "anthropic"
    if provider == "openai":
        return "openai"
    if provider == "ollama":
        return "local"
    if provider == "heuristic":
        return "cortex"
    # For CheaperInference, infer from model name
    model_lower = model.lower()
    if "gemini" in model_lower:
        return "google"
    if "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower:
        return "openai"
    if "claude" in model_lower:
        return "anthropic"
    if "llama" in model_lower or "mistral" in model_lower:
        return "meta"
    return "unknown"


# ---------------------------------------------------------------------------
# Per-incident LLM call budget
# ---------------------------------------------------------------------------
class LLMCallBudget:
    """
    Thread-safe per-incident call counter.

    Prevents a single incident from generating unbounded LLM calls.
    Budget slots (configurable):
        diagnosis       → 1 call
        self_critique   → 1 call
        semantic_review → 1 call
        optional_retry  → 1 call
    Total default = 4 per incident.
    """

    def __init__(self, max_calls: int = 4) -> None:
        self.max_calls = max_calls
        self._counts: dict[str, int] = {}
        self._lock = threading.Lock()

    def can_call(self, incident_id: str) -> tuple[bool, int]:
        """Returns (allowed, current_count). Thread-safe."""
        with self._lock:
            count = self._counts.get(incident_id, 0)
            return count < self.max_calls, count

    def record_call(self, incident_id: str) -> int:
        """Increment and return the new count. Thread-safe."""
        with self._lock:
            count = self._counts.get(incident_id, 0) + 1
            self._counts[incident_id] = count
            return count

    def reserve(self, incident_id: str, limit: int | None = None) -> bool:
        """Atomically reserve each network attempt, including retries/fallbacks."""
        with self._lock:
            maximum = self.max_calls if limit is None else limit
            count = self._counts.get(incident_id, 0)
            if count >= maximum:
                return False
            self._counts[incident_id] = count + 1
            return True

    def reset(self, incident_id: str) -> None:
        with self._lock:
            self._counts.pop(incident_id, None)

    def get_count(self, incident_id: str) -> int:
        with self._lock:
            return self._counts.get(incident_id, 0)


# ---------------------------------------------------------------------------
# Cost aggregation (per-incident)
# ---------------------------------------------------------------------------
class IncidentCostTracker:
    """Accumulates cost and call metadata per incident."""

    def __init__(self) -> None:
        self._data: dict[str, dict] = {}
        self._lock = threading.Lock()

    def record(
        self,
        incident_id: str,
        *,
        provider: str,
        model: str,
        purpose: str,
        input_tokens: Optional[int],
        output_tokens: Optional[int],
        latency_ms: float,
        billed_cost_usd: Optional[Decimal],
        fallback_used: bool,
        status: str,
    ) -> None:
        with self._lock:
            entry = self._data.setdefault(
                incident_id,
                {
                    "calls": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_cost_usd": Decimal("0"),
                    "provider_failures": 0,
                    "fallback_count": 0,
                    "events": [],
                },
            )
            entry["calls"] += 1
            entry["total_input_tokens"] += input_tokens or 0
            entry["total_output_tokens"] += output_tokens or 0
            if billed_cost_usd is not None:
                entry["total_cost_usd"] += billed_cost_usd
            if fallback_used:
                entry["fallback_count"] += 1
            if status != "ok":
                entry["provider_failures"] += 1
            entry["events"].append(
                {
                    "type": "llm_request_completed",
                    "incident_id": incident_id,
                    "provider": provider,
                    "model": model,
                    "purpose": purpose,
                    "latency_ms": round(latency_ms, 2),
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "billed_cost_usd": str(billed_cost_usd) if billed_cost_usd else None,
                    "fallback_used": fallback_used,
                    "status": status,
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            )

    def get(self, incident_id: str) -> dict:
        with self._lock:
            d = self._data.get(incident_id, {})
            if not d:
                return {}
            return {
                "calls": d["calls"],
                "total_input_tokens": d["total_input_tokens"],
                "total_output_tokens": d["total_output_tokens"],
                "total_cost_usd": str(d["total_cost_usd"]) if d["total_cost_usd"] else None,
                "provider_failures": d["provider_failures"],
                "fallback_count": d["fallback_count"],
            }


# Module-level singletons
llm_call_budget = LLMCallBudget(max_calls=4)
incident_cost_tracker = IncidentCostTracker()
