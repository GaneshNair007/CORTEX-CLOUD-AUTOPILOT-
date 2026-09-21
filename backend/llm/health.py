"""
CORTEX LLM — Provider health model and circuit breaker.

ProviderHealth: typed health state for a single provider.
CircuitBreaker: per-provider open/closed/half-open state machine.
LLMHealthMonitor: aggregates health across all configured providers.

IMPORTANT: No secret values are ever included in health responses.
"""

from __future__ import annotations

import logging
import threading
import time
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Health status enum
# ---------------------------------------------------------------------------
class ProviderStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
    CONFIGURED = "CONFIGURED"  # Not yet probed
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    INVALID_CREDENTIAL = "INVALID_CREDENTIAL"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    DISABLED = "DISABLED"


# ---------------------------------------------------------------------------
# Circuit breaker states
# ---------------------------------------------------------------------------
class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing; requests blocked
    HALF_OPEN = "HALF_OPEN"  # Testing recovery


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------
class CircuitBreaker:
    """
    Per-provider lightweight circuit breaker.

    Transitions:
        CLOSED  → OPEN      after failure_threshold consecutive failures
        OPEN    → HALF_OPEN after recovery_timeout_s seconds
        HALF_OPEN → CLOSED  on first success
        HALF_OPEN → OPEN    on failure in half-open state
    """

    def __init__(
        self,
        provider: str,
        failure_threshold: int = 3,
        recovery_timeout_s: float = 60.0,
    ) -> None:
        self.provider = provider
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._probe_inflight = False
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._get_state_locked()

    def _get_state_locked(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if (
                self._last_failure_time is not None
                and time.monotonic() - self._last_failure_time >= self.recovery_timeout_s
            ):
                self._state = CircuitState.HALF_OPEN
        return self._state

    def allow_request(self) -> bool:
        """Returns True if a request should be attempted."""
        with self._lock:
            state = self._get_state_locked()
            if state == CircuitState.HALF_OPEN:
                if self._probe_inflight:
                    return False
                self._probe_inflight = True
                return True
            return state == CircuitState.CLOSED

    def cancel_probe(self) -> None:
        """Release a half-open probe when a local budget prevents the request."""
        with self._lock:
            self._probe_inflight = False

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._probe_inflight = False
            if self._state == CircuitState.HALF_OPEN:
                logger.info("Circuit CLOSED for provider %r (recovery successful)", self.provider)
            self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._probe_inflight = False
            self._last_failure_time = time.monotonic()
            if self._state == CircuitState.HALF_OPEN or self._failure_count >= self.failure_threshold:
                if self._state != CircuitState.OPEN:
                    logger.warning(
                        "Circuit OPEN for provider %r after %d failures",
                        self.provider,
                        self._failure_count,
                    )
                self._state = CircuitState.OPEN

    def safe_dict(self) -> dict:
        return {
            "provider": self.provider,
            "circuit_state": self.state.value,
            "failure_count": self._failure_count,
        }


# ---------------------------------------------------------------------------
# Per-provider health record
# ---------------------------------------------------------------------------
class ProviderHealth:
    __slots__ = (
        "provider",
        "configured",
        "credential_present",
        "credential_validated",
        "model",
        "model_available",
        "last_success_at",
        "last_failure_at",
        "last_error_code",
        "latency_ms",
        "circuit_state",
        "status",
        "is_paid",
        "cost_type",
    )

    def __init__(
        self,
        *,
        provider: str,
        configured: bool = False,
        credential_present: bool = False,
        credential_validated: bool = False,
        model: Optional[str] = None,
        model_available: Optional[bool] = None,
        last_success_at: Optional[float] = None,
        last_failure_at: Optional[float] = None,
        last_error_code: Optional[str] = None,
        latency_ms: Optional[float] = None,
        circuit_state: CircuitState = CircuitState.CLOSED,
        status: ProviderStatus = ProviderStatus.UNKNOWN,
        is_paid: bool = False,
        cost_type: str = "free",
    ) -> None:
        self.provider = provider
        self.configured = configured
        self.credential_present = credential_present
        self.credential_validated = credential_validated
        self.model = model
        self.model_available = model_available
        self.last_success_at = last_success_at
        self.last_failure_at = last_failure_at
        self.last_error_code = last_error_code
        self.latency_ms = latency_ms
        self.circuit_state = circuit_state
        self.status = status
        self.is_paid = is_paid
        self.cost_type = cost_type

    def to_api_dict(self) -> dict:
        """Safe serialization — no secrets."""
        return {
            "provider": self.provider,
            "configured": self.configured,
            "credential_present": self.credential_present,
            "credential_validated": self.credential_validated,
            "model": self.model,
            "model_available": self.model_available,
            "last_success_at": self.last_success_at,
            "last_failure_at": self.last_failure_at,
            "last_error_code": self.last_error_code,
            "latency_ms": round(self.latency_ms, 2) if self.latency_ms else None,
            "circuit_state": self.circuit_state.value,
            "status": self.status.value,
            "is_paid": self.is_paid,
            "cost_type": self.cost_type,
        }


# ---------------------------------------------------------------------------
# Health monitor: aggregates all provider health
# ---------------------------------------------------------------------------
class LLMHealthMonitor:
    """
    Tracks health state for all configured providers.
    Updated by LLMClient after each generate() call.
    """

    def __init__(self) -> None:
        self._health: dict[str, ProviderHealth] = {}
        self._circuits: dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()
        self._last_route: dict = {}

    def record_route(self, provider: str, model: str, fallback_used: bool, latency_ms: float) -> None:
        with self._lock:
            self._last_route = {"provider": provider, "model": model, "fallback_used": fallback_used,
                                "latency_ms": latency_ms, "completed_at": time.time()}

    def last_route(self) -> dict:
        with self._lock:
            return dict(self._last_route)

    def get_or_create_circuit(self, provider: str) -> CircuitBreaker:
        with self._lock:
            if provider not in self._circuits:
                self._circuits[provider] = CircuitBreaker(provider)
            return self._circuits[provider]

    def update_success(self, provider: str, model: str, latency_ms: float) -> None:
        with self._lock:
            existing = self._health.get(provider)
            self._health[provider] = ProviderHealth(
                provider=provider,
                configured=True,
                credential_present=provider not in ("heuristic", "ollama"),
                credential_validated=provider not in ("heuristic", "ollama"),
                model=model,
                model_available=True,
                last_success_at=time.time(),
                last_failure_at=existing.last_failure_at if existing else None,
                last_error_code=None,
                latency_ms=latency_ms,
                circuit_state=self._circuits.get(provider, CircuitBreaker(provider)).state,
                status=ProviderStatus.DEGRADED if provider == "heuristic" else ProviderStatus.HEALTHY,
                is_paid=self._get_is_paid(provider),
                cost_type=self._get_cost_type(provider),
            )
        if provider in self._circuits:
            self._circuits[provider].record_success()

    def update_failure(self, provider: str, error_code: str, model: Optional[str] = None) -> None:
        with self._lock:
            existing = self._health.get(provider)
            circuit = self._circuits.get(provider)
            self._health[provider] = ProviderHealth(
                provider=provider,
                configured=True,
                credential_present=existing.credential_present if existing else True,
                credential_validated=bool(existing and existing.credential_validated and error_code != "AUTHENTICATION_ERROR"),
                model=model or (existing.model if existing else None),
                last_success_at=existing.last_success_at if existing else None,
                last_failure_at=time.time(),
                last_error_code=error_code,
                circuit_state=circuit.state if circuit else CircuitState.CLOSED,
                status={"RATE_LIMITED": ProviderStatus.RATE_LIMITED, "QUOTA_EXHAUSTED": ProviderStatus.QUOTA_EXHAUSTED,
                        "AUTHENTICATION_ERROR": ProviderStatus.INVALID_CREDENTIAL,
                        "MODEL_UNAVAILABLE": ProviderStatus.MODEL_UNAVAILABLE}.get(error_code, ProviderStatus.UNAVAILABLE),
                is_paid=self._get_is_paid(provider),
                cost_type=self._get_cost_type(provider),
            )
        cb = self.get_or_create_circuit(provider)
        cb.record_failure()

    def register_provider(self, provider: str, *, configured: bool, credential_present: bool, model: Optional[str], is_paid: bool) -> None:
        """Register a provider at startup before any calls are made."""
        with self._lock:
            if provider not in self._health:
                self._health[provider] = ProviderHealth(
                    provider=provider,
                    configured=configured,
                    credential_present=credential_present,
                    model=model,
                    status=ProviderStatus.CONFIGURED if configured else ProviderStatus.UNAVAILABLE,
                    is_paid=is_paid,
                    cost_type=self._get_cost_type(provider),
                )
            self.get_or_create_circuit(provider)

    def get_health(self, provider: str) -> Optional[ProviderHealth]:
        with self._lock:
            return self._health.get(provider)

    def get_all_health(self) -> dict[str, ProviderHealth]:
        with self._lock:
            return dict(self._health)

    def is_circuit_open(self, provider: str) -> bool:
        cb = self._circuits.get(provider)
        return cb is not None and not cb.allow_request()

    @staticmethod
    def _get_is_paid(provider: str) -> bool:
        return provider in ("cheaperinference", "openai", "anthropic")

    @staticmethod
    def _get_cost_type(provider: str) -> str:
        return {
            "gemini": "free-tier / paid",
            "nvidia": "hosted quota; billing depends on account",
            "cheaperinference": "wallet-backed",
            "openai": "usage-based",
            "anthropic": "usage-based",
            "ollama": "local / free",
            "heuristic": "free / no network",
        }.get(provider, "unknown")


# Module-level singleton
llm_health_monitor = LLMHealthMonitor()
