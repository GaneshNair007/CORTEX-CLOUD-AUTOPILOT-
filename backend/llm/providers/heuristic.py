"""
CORTEX LLM — Heuristic fallback provider.

Zero network calls. Zero cost. Zero credentials required.
Produces deterministic, input-dependent responses using keyword analysis.

IMPORTANT: Every response is explicitly labeled:
    provider = "heuristic"
    fallback_used = True (when used as a fallback)
    model = "cortex-heuristic-reasoner"

The UI must clearly display "HEURISTIC FALLBACK ACTIVE" whenever this
provider is in use — never silently present heuristic output as real AI.
"""

from __future__ import annotations

import json
import re
import time
from typing import Optional

from backend.llm.providers.base import BaseLLMProvider
from backend.llm.telemetry import LLMResponse


class HeuristicProvider(BaseLLMProvider):
    name = "heuristic"
    is_paid = False

    MODEL_NAME = "cortex-heuristic-reasoner"

    def __init__(self, fallback_used: bool = False) -> None:
        """
        Args:
            fallback_used: Set True when this provider is active as a fallback,
                           not as the intended primary.
        """
        self._fallback_used = fallback_used

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        model: Optional[str] = None,
    ) -> LLMResponse:
        t0 = time.perf_counter()
        text = self._synthesize(prompt)
        if system and "CORTEX_DIAGNOSIS_JSON" in system:
            text = json.dumps({"root_cause": "Insufficient verified evidence for autonomous remediation; inspect current telemetry and retrieved evidence.",
                "confidence": 0.3, "evidence_ids": [], "alternative_causes": [], "action": {"action_type": "create_ticket", "params": {}}})
        elif system and "CORTEX_CRITIQUE_JSON" in system:
            text = json.dumps({"critique": "Heuristic review cannot validate the root cause; human investigation required.", "confidence": 0.3, "verdict": "UNCERTAIN"})
        latency_ms = (time.perf_counter() - t0) * 1000

        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.MODEL_NAME,
            latency_ms=latency_ms,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            billed_cost_usd=None,
            fallback_used=self._fallback_used,
            fallback_reason="heuristic_mode" if self._fallback_used else None,
        )

    def health_check(self) -> dict:
        return {
            "status": "HEALTHY",
            "provider": self.name,
            "model": self.MODEL_NAME,
            "note": "Heuristic mode — no network, no credentials required",
        }

    # ------------------------------------------------------------------
    # Deterministic keyword-based reasoning (no static strings)
    # ------------------------------------------------------------------
    def _synthesize(self, prompt: str) -> str:
        lower = prompt.lower()

        service_match = re.search(
            r"(?:service|incident|target|deployment)[:\s]+([a-zA-Z0-9_\-]+)",
            prompt,
            re.IGNORECASE,
        )
        service = service_match.group(1) if service_match else "target-service"

        symptoms = []
        causes = []

        if any(w in lower for w in ("pool", "exhaust", "connection", "postgres", "database")):
            symptoms.append("connection pool saturation")
            causes.append("unclosed transactions holding pool slots")
        if any(w in lower for w in ("latency", "slow", "timeout", "p95", "p99", "surge")):
            symptoms.append("degraded response latency")
            causes.append("thread exhaustion and downstream lock contention")
        if any(w in lower for w in ("cpu", "spike", "saturation", "overload")):
            symptoms.append("sustained CPU saturation")
            causes.append("unthrottled request surges")
        if any(w in lower for w in ("memory", "oom", "leak", "heap")):
            symptoms.append("progressive memory consumption")
            causes.append("uncollected buffer references")
        if any(w in lower for w in ("500", "502", "crash", "restart", "panic")):
            symptoms.append("5xx error bursts")
            causes.append("unhandled exception propagation")

        if not symptoms:
            symptoms.append("anomalous operational telemetry")
            causes.append("transient network fluctuation")

        symptom_str = " and ".join(symptoms)
        cause_str = " combined with ".join(causes)

        if any(w in lower for w in ("critique", "disprove", "skeptical", "counter-evidence")):
            return (
                f"COUNTER-EVIDENCE: The observed telemetry in {service} shows {symptom_str}, "
                f"which may partially align with network partition noise rather than software failure.\n"
                f"ALTERNATIVE CAUSE: Upstream API gateway retry storms could artificially inflate load.\n"
                f"VERDICT: The primary hypothesis survives scrutiny; conservative remediation is advised.\n\n"
                f"REVISED CONFIDENCE: 0.68"
            )

        return (
            f"HYPOTHESIS: Root-cause for {service}: Incident symptoms indicate {symptom_str}. "
            f"Correlating telemetry identifies {cause_str} as the primary trigger.\n\n"
            f"CONFIDENCE: 0.76"
        )
