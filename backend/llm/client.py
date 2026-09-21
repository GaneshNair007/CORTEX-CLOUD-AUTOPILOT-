"""
CORTEX LLM Client — Explicit, Observable, Provider-Independent

Replaces the old credential-selection-bug-prone LLMClient.

Architecture:
  - Provider identity is explicit: "gemini" ≠ "cheaperinference" ≠ "openai"
  - Credentials are provider-specific: Gemini key NEVER used for OpenAI calls
  - CheaperInference is a first-class provider, not disguised as OpenAI
  - Paid fallback is OFF by default (ALLOW_PAID_LLM_FALLBACK=false)
  - Circuit breaker prevents hammering failing providers
  - Prompt sanitizer runs before every external call
  - Every response includes: provider, model, fallback_used, latency_ms
  - Heuristic fallback is always labeled — never presented as real AI

Provider selection order (configurable via LLM_PRIMARY_PROVIDER + LLM_FALLBACK_PROVIDERS):
  1. Primary provider (default: gemini)
  2. Fallback providers in order (default: ollama, heuristic)
     - Paid fallback (cheaperinference, openai, anthropic) requires
       ALLOW_PAID_LLM_FALLBACK=true to be activated
"""

from __future__ import annotations

import concurrent.futures
import datetime
import logging
import os
import time
import warnings
from typing import Optional

from backend.config.settings import settings
from backend.llm.errors import (
    AuthenticationError,
    ConfigurationError,
    InsufficientBalanceError,
    InvalidRequestError,
    LLMBudgetExhaustedError,
    LLMError,
    ModelUnavailableError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    QuotaExhaustedError,
    RateLimitedError,
    RETRYABLE_CODES,
)
from backend.llm.health import CircuitState, ProviderStatus, llm_health_monitor
from backend.llm.providers.anthropic import AnthropicProvider
from backend.llm.providers.base import BaseLLMProvider
from backend.llm.providers.cheaperinference import CheaperInferenceProvider
from backend.llm.providers.gemini import GeminiProvider
from backend.llm.providers.heuristic import HeuristicProvider
from backend.llm.providers.ollama import OllamaProvider
from backend.llm.providers.openai import OpenAIProvider
from backend.llm.providers.nvidia import NvidiaNIMProvider
from backend.llm.sanitizer import sanitize_prompt
from backend.llm.telemetry import LLMResponse, llm_call_budget, incident_cost_tracker

try:
    from backend.tools.actions import emit_event
except ImportError:
    def emit_event(event: dict) -> None:
        pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry policy — only transient errors are retried
# ---------------------------------------------------------------------------
_RETRYABLE_ERRORS = (RateLimitedError, ProviderTimeoutError, ProviderUnavailableError)
_NON_RETRYABLE_ERRORS = (
    AuthenticationError, InvalidRequestError, InsufficientBalanceError, ModelUnavailableError
)

_BACKOFF_BASE_S = 0.5  # 500ms → 1s → 2s


def _backoff_sleep(attempt: int) -> None:
    """Exponential backoff with jitter."""
    import random
    delay = _BACKOFF_BASE_S * (2 ** attempt)
    jitter = random.uniform(0, delay * 0.2)
    time.sleep(delay + jitter)


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------
def _build_provider(provider_name: str, *, fallback: bool = False) -> Optional[BaseLLMProvider]:
    """
    Construct a provider instance for the given provider name.
    Returns None if the provider cannot be constructed (missing credential, etc.).
    Raises ConfigurationError on credential family mismatch.
    """
    cfg = settings.llm

    if provider_name == "nvidia":
        key = os.environ.get("NVIDIA_API_KEY")
        if not key:
            return None
        return NvidiaNIMProvider(api_key=key, model=cfg.nvidia_model,
                                 base_url=cfg.nvidia_base_url, timeout=cfg.timeout_seconds)

    if provider_name == "gemini":
        key = cfg.credential if cfg.provider == "gemini" else (
            os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        )
        if not key:
            return None
        return GeminiProvider(
            api_key=key,
            model=cfg.gemini_model,
            timeout=cfg.timeout_seconds,
        )

    if provider_name == "cheaperinference":
        key = cfg.credential if cfg.provider == "cheaperinference" else os.environ.get("CHEAPERINFERENCE_API_KEY")
        if not key:
            return None
        return CheaperInferenceProvider(
            api_key=key,
            model=cfg.cheaperinference_model,
            base_url=cfg.cheaperinference_base_url,
            timeout=cfg.timeout_seconds,
            usage_api_key=cfg.cheaperinference_usage_key,
        )

    if provider_name == "openai":
        # Safety check: do not use OpenAI provider if base URL is CheaperInference
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if "cheaperinference.com" in base_url.lower():
            raise ConfigurationError(
                "OPENAI_BASE_URL points to CheaperInference but provider=openai. "
                "Set LLM_PROVIDER=cheaperinference.",
                provider="openai",
            )
        key = cfg.credential if cfg.provider == "openai" else os.environ.get("OPENAI_API_KEY")
        if not key:
            return None
        return OpenAIProvider(
            api_key=key,
            model=cfg.openai_model,
            base_url=base_url,
            timeout=cfg.timeout_seconds,
        )

    if provider_name == "anthropic":
        key = cfg.credential if cfg.provider == "anthropic" else os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            return None
        return AnthropicProvider(
            api_key=key,
            model=cfg.anthropic_model,
            timeout=cfg.timeout_seconds,
        )

    if provider_name == "ollama":
        return OllamaProvider(
            host=cfg.ollama_host,
            model=cfg.ollama_model,
            timeout=cfg.timeout_seconds * 2,
        )

    if provider_name == "heuristic":
        return HeuristicProvider(fallback_used=fallback)

    return None


# ---------------------------------------------------------------------------
# LLMClient — public interface (backward-compatible with existing callers)
# ---------------------------------------------------------------------------
class LLMClient:
    """
    Unified LLM client with explicit provider identity, fallback chain,
    circuit breaker, budget enforcement, and prompt sanitization.

    Backward-compatible attributes:
        self.mode   → provider name (was previously "gemini"/"openai"/"mock")
        self.model  → active model name
        self.api_key → always None (credential access moved to provider instances)
    """

    def __init__(
        self,
        mode: Optional[str] = None,
        model: Optional[str] = None,
        host: Optional[str] = None,
        api_key: Optional[str] = None,  # Accepted for compat but not stored/used
    ) -> None:
        if api_key:
            logger.warning(
                "LLMClient(api_key=...) is deprecated. "
                "Set credentials via environment variables only."
            )

        cfg = settings.llm

        # Resolve provider — explicit argument overrides global config
        if mode:
            # Accept legacy mode names
            _legacy_map = {
                "nvidia": "nvidia",
                "mock": "heuristic",
                "heuristic": "heuristic",
                "gemini": "gemini",
                "openai": "openai",
                "anthropic": "anthropic",
                "ollama": "ollama",
                "cheaperinference": "cheaperinference",
            }
            if mode.lower() not in _legacy_map:
                raise LLMError(
                    f"Unknown provider mode {mode!r}. "
                    "Expected: gemini, cheaperinference, openai, anthropic, ollama, heuristic",
                    provider="unknown",
                )
            self._provider_name = _legacy_map[mode.lower()]
        else:
            self._provider_name = cfg.provider

        # Build the primary provider
        self._primary: Optional[BaseLLMProvider] = None
        try:
            self._primary = _build_provider(self._provider_name)
        except ConfigurationError as exc:
            logger.error("Provider configuration error: %s", exc)

        # Expose legacy attributes that existing code depends on
        self.mode: str = self._provider_name
        self.model: str = model or getattr(self._primary, "model", cfg.active_model)
        self.api_key: None = None  # Never expose credentials

        # Model override from constructor
        if model and self._primary:
            # Store for use in generate()
            self._model_override = model
        else:
            self._model_override: Optional[str] = None

        # Host override for Ollama
        if host and isinstance(self._primary, OllamaProvider):
            self._primary.host = host.rstrip("/")

        # Register with health monitor
        llm_health_monitor.register_provider(
            self._provider_name,
            configured=self._primary is not None,
            credential_present=self._primary is not None and self._provider_name not in ("heuristic", "ollama"),
            model=self.model,
            is_paid=getattr(self._primary, "is_paid", False) if self._primary else False,
        )

        logger.info(
            "LLMClient initialized: provider=%r model=%r fallbacks=%r paid_fallback=%s",
            self._provider_name,
            self.model,
            cfg.fallback_providers,
            cfg.allow_paid_llm_fallback,
        )

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        incident_id: Optional[str] = None,
        purpose: str = "generate",
    ) -> dict:
        """
        Generate a completion with full fallback, retry, budget, and sanitization.

        Returns a dict with at minimum: {"text": ..., "mode": ..., "model": ...}
        for backward compatibility, plus all LLMResponse observability fields.
        """
        cfg = settings.llm
        effective_max_tokens = min(
            max_tokens or cfg.max_output_tokens,
            cfg.max_output_tokens,
        )

        # Prompt sanitization (defense-in-depth)
        clean_prompt, clean_system = sanitize_prompt(prompt, system)

        purpose_provider = {"diagnosis": cfg.diagnosis_provider, "critique": cfg.critique_provider,
                            "semantic_review": cfg.semantic_review_provider}.get(purpose, self._provider_name)
        primary = self._primary if purpose_provider == self._provider_name else _build_provider(purpose_provider)
        purpose_model = {"diagnosis": cfg.diagnosis_model, "critique": cfg.critique_model}.get(purpose) or self._model_override
        selected_model = purpose_model or getattr(primary, "model", None)
        if selected_model and cfg.allowed_models and selected_model not in cfg.allowed_models:
            raise ConfigurationError("Requested model is not in CORTEX_ALLOWED_MODELS", provider=purpose_provider)
        if incident_id and llm_call_budget.get_count(incident_id) >= cfg.max_requests_per_incident:
            resp = HeuristicProvider(fallback_used=True).generate(clean_prompt, system=clean_system, max_tokens=effective_max_tokens)
            resp.fallback_reason = "incident_call_budget_exhausted"
            self._record_telemetry(resp, incident_id, purpose, "ok")
            self._emit_telemetry(resp, incident_id, purpose)
            return resp.to_dict()

        # Try primary provider with retries
        response = self._try_with_retries(
            primary,
            clean_prompt,
            system=clean_system,
            temperature=temperature,
            max_tokens=effective_max_tokens,
            model=purpose_model,
            incident_id=incident_id,
            purpose=purpose,
        )

        if response is not None:
            self._record_telemetry(response, incident_id, purpose, "ok")
            self._emit_telemetry(response, incident_id, purpose)
            return response.to_dict()

        # Primary failed — run fallback chain
        response = self._run_fallback_chain(
            clean_prompt,
            system=clean_system,
            temperature=temperature,
            max_tokens=effective_max_tokens,
            incident_id=incident_id,
            purpose=purpose,
        )

        self._record_telemetry(response, incident_id, purpose, "ok")
        self._emit_telemetry(response, incident_id, purpose)
        return response.to_dict()

    def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> dict:
        """Alias for generate() — backward compatibility."""
        return self.generate(prompt, system=system, temperature=temperature, max_tokens=max_tokens)

    def generate_batch(
        self,
        prompts: list[str],
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
    ) -> dict:
        """Run multiple prompts concurrently."""
        t0 = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(prompts), 8)) as pool:
            futures = [
                pool.submit(self.generate, p, system, temperature, max_tokens)
                for p in prompts
            ]
            results = [f.result() for f in futures]
        wall = time.perf_counter() - t0
        return {
            "results": results,
            "wall_clock_s": round(wall, 3),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _try_with_retries(
        self,
        provider: Optional[BaseLLMProvider],
        prompt: str,
        *,
        system: Optional[str],
        temperature: float,
        max_tokens: int,
        model: Optional[str] = None,
        incident_id: Optional[str] = None,
        purpose: str = "generate",
    ) -> Optional[LLMResponse]:
        """Attempt a call with exponential backoff retry. Returns None on total failure."""
        if provider is None:
            return None

        provider_name = provider.name
        circuit = llm_health_monitor.get_or_create_circuit(provider_name)

        if not circuit.allow_request():
            logger.warning(
                "Circuit OPEN for provider %r — skipping without calling.",
                provider_name,
            )
            return None

        cfg = settings.llm
        last_exc: Optional[LLMError] = None

        if getattr(provider, "is_paid", False) and cfg.max_cost_per_incident_usd is not None:
            # There is no trustworthy pre-call price bound in these adapters.
            # A hard dollar cap must fail closed instead of treating missing cost as zero.
            circuit.cancel_probe()
            self._record_failure(provider_name, model, incident_id, purpose, "COST_BOUND_UNAVAILABLE", 0)
            return None

        for attempt in range(cfg.max_retries + 1):
            if incident_id and provider_name != "heuristic" and not llm_call_budget.reserve(incident_id, cfg.max_requests_per_incident):
                circuit.cancel_probe()
                return None
            started = time.perf_counter()
            try:
                resp = provider.generate(
                    prompt,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model=model,
                )
                llm_health_monitor.update_success(
                    provider_name, resp.model, resp.latency_ms
                )
                from backend.llm.sanitizer import sanitize
                resp.text, _ = sanitize(resp.text)
                return resp
            except _NON_RETRYABLE_ERRORS as exc:
                self._record_failure(provider_name, model, incident_id, purpose, exc.error_code, started)
                # Never retry auth failures, invalid requests, etc.
                llm_health_monitor.update_failure(provider_name, exc.error_code, model)
                logger.error(
                    "Non-retryable error from %r: %s", provider_name, exc.error_code
                )
                return None
            except _RETRYABLE_ERRORS as exc:
                self._record_failure(provider_name, model, incident_id, purpose, exc.error_code, started)
                last_exc = exc
                llm_health_monitor.update_failure(provider_name, exc.error_code, model)
                if attempt < cfg.max_retries:
                    logger.info(
                        "Retryable error from %r (attempt %d/%d): %s — backing off",
                        provider_name, attempt + 1, cfg.max_retries + 1, exc.error_code,
                    )
                    _backoff_sleep(attempt)
            except LLMError as exc:
                self._record_failure(provider_name, model, incident_id, purpose, exc.error_code, started)
                llm_health_monitor.update_failure(provider_name, exc.error_code, model)
                logger.warning("LLM error from %r: %s", provider_name, exc.error_code)
                return None
            except Exception as exc:
                self._record_failure(provider_name, model, incident_id, purpose, "UNKNOWN_PROVIDER_ERROR", started)
                llm_health_monitor.update_failure(provider_name, "UNKNOWN_PROVIDER_ERROR", model)
                logger.error("Unexpected provider failure: provider=%s type=%s", provider_name, type(exc).__name__)
                return None

        logger.warning(
            "All %d retries exhausted for provider %r.", cfg.max_retries + 1, provider_name
        )
        return None

    def _record_failure(self, provider: str, model: str | None, incident_id: str | None,
                        purpose: str, error_code: str, started: float) -> None:
        """Record each failed attempt without request bodies, responses or secrets."""
        latency = (time.perf_counter() - started) * 1000 if started else 0
        if incident_id:
            incident_cost_tracker.record(incident_id, provider=provider, model=model or "configured",
                purpose=purpose, input_tokens=None, output_tokens=None, latency_ms=latency,
                billed_cost_usd=None, fallback_used=False, status=error_code)
        emit_event({"type": "llm_request_failed", "incident_id": incident_id,
                    "payload": {"provider": provider, "purpose": purpose, "error_code": error_code,
                                "latency_ms": round(latency, 2)}})

    def _run_fallback_chain(
        self,
        prompt: str,
        *,
        system: Optional[str],
        temperature: float,
        max_tokens: int,
        incident_id: Optional[str],
        purpose: str,
    ) -> LLMResponse:
        """
        Try fallback providers in order.

        Paid fallbacks are skipped unless ALLOW_PAID_LLM_FALLBACK=true.
        Always returns a response (final fallback is always heuristic).
        """
        cfg = settings.llm
        paid_providers = {"cheaperinference", "openai", "anthropic"}

        for fallback_name in cfg.fallback_providers:
            if fallback_name == self._provider_name:
                continue  # Skip: already tried as primary

            is_paid_fallback = fallback_name in paid_providers
            if is_paid_fallback and not cfg.allow_paid_llm_fallback:
                logger.info(
                    "Skipping paid fallback %r — ALLOW_PAID_LLM_FALLBACK=false",
                    fallback_name,
                )
                continue

            fallback_provider = _build_provider(fallback_name, fallback=True)
            if fallback_provider is None:
                logger.info("Fallback %r not configured — skipping.", fallback_name)
                continue

            # For heuristic, always succeed
            if fallback_name == "heuristic":
                heuristic = HeuristicProvider(fallback_used=True)
                resp = heuristic.generate(
                    prompt, system=system, temperature=temperature, max_tokens=max_tokens
                )
                logger.warning(
                    "HEURISTIC FALLBACK ACTIVE for incident %s. "
                    "Primary provider %r was unavailable.",
                    incident_id or "unknown",
                    self._provider_name,
                )
                return resp

            resp = self._try_with_retries(
                fallback_provider,
                prompt,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                incident_id=incident_id,
                purpose=purpose,
            )
            if resp is not None:
                # Mark as fallback
                resp.fallback_used = True
                resp.fallback_reason = f"primary_{self._provider_name}_unavailable"
                logger.info(
                    "Fallback to %r succeeded for incident %s.",
                    fallback_name,
                    incident_id or "unknown",
                )
                return resp

        # Ultimate safety net — heuristic always works
        logger.warning(
            "All providers exhausted. Returning heuristic output. "
            "incident=%s provider=%r",
            incident_id or "unknown",
            self._provider_name,
        )
        heuristic = HeuristicProvider(fallback_used=True)
        return heuristic.generate(
            prompt, system=system, temperature=temperature, max_tokens=max_tokens
        )

    def _record_telemetry(
        self,
        resp: LLMResponse,
        incident_id: Optional[str],
        purpose: str,
        status: str,
    ) -> None:
        if incident_id:
            incident_cost_tracker.record(
                incident_id,
                provider=resp.provider,
                model=resp.model,
                purpose=purpose,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                latency_ms=resp.latency_ms,
                billed_cost_usd=resp.billed_cost_usd,
                fallback_used=resp.fallback_used,
                status=status,
            )

    def _emit_telemetry(
        self,
        resp: LLMResponse,
        incident_id: Optional[str],
        purpose: str,
    ) -> None:
        llm_health_monitor.record_route(resp.provider, resp.model, resp.fallback_used, resp.latency_ms)
        try:
            emit_event(
                {
                    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "type": "llm_request_completed",
                    "stage": "telemetry",
                    "incident_id": incident_id,
                    "gateway": resp.gateway,
                    "model_provider": resp.model_provider,
                    "model": resp.model,
                    "provider": resp.provider,
                    "latency_ms": resp.latency_ms,
                    "input_tokens": resp.input_tokens,
                    "output_tokens": resp.output_tokens,
                    "billed_cost_usd": str(resp.billed_cost_usd) if resp.billed_cost_usd else None,
                    "fallback_used": resp.fallback_used,
                    "fallback_reason": resp.fallback_reason,
                    "purpose": purpose,
                    # Legacy fields for backward-compat event consumers
                    "mode": resp.provider,
                    "tokens": resp.output_tokens,
                    "latency_s": round(resp.latency_ms / 1000, 4),
                }
            )
        except (OSError, ValueError) as exc:
            logger.warning("Could not persist LLM telemetry: %s", type(exc).__name__)

    def set_model(self, model: str) -> None:
        """Allow router to update the active model for this request."""
        self._model_override = model
        self.model = model
        if self._primary:
            self._primary.model = model
