"""
CORTEX Cloud Autopilot — Central Configuration
Single validated settings object loaded once at startup.

Config precedence (highest → lowest):
  1. Process environment variables
  2. backend/.env
  3. Safe defaults

No real secret is ever logged, printed, or stored in source code.
"""

from __future__ import annotations

import logging
import os
import warnings
from decimal import Decimal
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load .env files early — process env wins (override=False)
# ---------------------------------------------------------------------------
_BACKEND_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_DIR.parent

from backend.config.environment import load_environment
load_environment()


# ---------------------------------------------------------------------------
# Valid provider names
# ---------------------------------------------------------------------------
VALID_PROVIDERS = frozenset(
    {"nvidia", "gemini", "cheaperinference", "openai", "anthropic", "ollama", "heuristic"}
)


def _resolve_provider() -> str:
    """
    Resolve the canonical provider name from LLM_PROVIDER or legacy LLM_MODE.

    Priority:
      LLM_PROVIDER                           (explicit, preferred)
      LLM_MODE=openai + OPENAI_BASE_URL~cheaperinference.com → cheaperinference
      LLM_MODE=<value>                       (legacy, with deprecation warning)
      Auto-detect from which keys are present
    """
    explicit = (os.environ.get("LLM_PRIMARY_PROVIDER") or os.environ.get("LLM_PROVIDER", "")).strip().lower()
    if explicit:
        if explicit not in VALID_PROVIDERS:
            raise ValueError(
                f"LLM_PROVIDER={explicit!r} is not valid. "
                f"Choose from: {sorted(VALID_PROVIDERS)}"
            )
        return explicit

    legacy = os.environ.get("LLM_MODE", "").strip().lower()
    if legacy:
        # Translate legacy openai + CheaperInference URL → cheaperinference
        base_url = os.environ.get("OPENAI_BASE_URL", "").lower()
        if legacy == "openai" and "cheaperinference.com" in base_url:
            warnings.warn(
                "LLM_MODE=openai with OPENAI_BASE_URL pointing to cheaperinference.com "
                "is deprecated. Set LLM_PROVIDER=cheaperinference instead.",
                DeprecationWarning,
                stacklevel=3,
            )
            return "cheaperinference"

        mapping = {
            "nvidia": "nvidia",
            "gemini": "gemini",
            "openai": "openai",
            "anthropic": "anthropic",
            "ollama": "ollama",
            "mock": "heuristic",
            "heuristic": "heuristic",
        }
        if legacy in mapping:
            if legacy not in ("heuristic", "mock"):
                warnings.warn(
                    f"LLM_MODE={legacy!r} is deprecated. "
                    f"Set LLM_PROVIDER={mapping[legacy]!r} instead.",
                    DeprecationWarning,
                    stacklevel=3,
                )
            return mapping[legacy]

    # Auto-detect from present credentials
    if os.environ.get("NVIDIA_API_KEY"):
        return "nvidia"
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    if os.environ.get("CHEAPERINFERENCE_API_KEY"):
        return "cheaperinference"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OLLAMA_HOST"):
        return "ollama"

    return "nvidia"


def _get_credential_for_provider(provider: str) -> Optional[str]:
    """
    Return the correct credential for the given provider.
    Never returns a credential that belongs to a different provider family.
    """
    if provider == "nvidia":
        return os.environ.get("NVIDIA_API_KEY")
    if provider == "gemini":
        return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if provider == "cheaperinference":
        return os.environ.get("CHEAPERINFERENCE_API_KEY")
    if provider == "openai":
        return os.environ.get("OPENAI_API_KEY")
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_API_KEY")
    # ollama and heuristic do not use API keys
    return None


def _parse_fallback_list(raw: str) -> list[str]:
    providers = [p.strip().lower() for p in raw.split(",") if p.strip()]
    invalid = [p for p in providers if p not in VALID_PROVIDERS]
    if invalid:
        raise ValueError(f"Invalid fallback providers: {invalid}")
    return providers


# ---------------------------------------------------------------------------
# LLM Settings dataclass (plain class — no pydantic-settings dependency risk)
# ---------------------------------------------------------------------------
class LLMSettings:
    """Validated LLM provider configuration resolved from environment."""

    def __init__(self) -> None:
        self.provider: str = _resolve_provider()
        self.credential: Optional[str] = _get_credential_for_provider(self.provider)

        # Provider-specific config
        self.nvidia_base_url = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self.nvidia_model = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
        self.gemini_model: str = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self.cheaperinference_base_url: str = os.environ.get(
            "CHEAPERINFERENCE_BASE_URL", "https://api.cheaperinference.com/v1"
        )
        self.cheaperinference_model: str = os.environ.get(
            "CHEAPERINFERENCE_MODEL", "gemini-2.0-flash"
        )
        self.cheaperinference_usage_key: Optional[str] = os.environ.get(
            "CHEAPERINFERENCE_USAGE_API_KEY"
        )
        self.openai_base_url: str = os.environ.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )
        self.openai_model: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.anthropic_model: str = os.environ.get(
            "ANTHROPIC_MODEL", "claude-3-5-haiku-latest"
        )
        self.ollama_host: str = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_model: str = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

        # Fallback chain
        raw_fallbacks = os.environ.get(
            "LLM_FALLBACK_PROVIDERS", "ollama,heuristic"
        )
        self.fallback_providers: list[str] = _parse_fallback_list(raw_fallbacks)

        # Cost guard: paid fallback is OFF by default
        self.allow_paid_llm_fallback: bool = (
            os.environ.get("ALLOW_PAID_LLM_FALLBACK", "false").lower() == "true"
        )

        # Per-request limits
        self.timeout_seconds: float = float(
            os.environ.get("CORTEX_LLM_TIMEOUT_SECONDS", "30")
        )
        self.max_retries: int = int(os.environ.get("CORTEX_LLM_MAX_RETRIES", "2"))
        self.max_output_tokens: int = int(
            os.environ.get("CORTEX_LLM_MAX_OUTPUT_TOKENS", "512")
        )
        self.max_requests_per_incident: int = int(
            os.environ.get("CORTEX_LLM_MAX_REQUESTS_PER_INCIDENT", "4")
        )

        # Optional: per-purpose model overrides
        self.diagnosis_model: Optional[str] = os.environ.get("DIAGNOSIS_MODEL")
        self.critique_model: Optional[str] = os.environ.get("CRITIQUE_MODEL")
        self.diagnosis_provider = os.environ.get("DIAGNOSIS_PROVIDER", self.provider)
        self.critique_provider = os.environ.get("CRITIQUE_PROVIDER", self.provider)
        self.semantic_review_provider = os.environ.get("SEMANTIC_REVIEW_PROVIDER", self.provider)
        self.enable_semantic_review = os.environ.get("ENABLE_SEMANTIC_REVIEW", "false").lower() == "true"

        # Cost guard
        self.max_cost_per_incident_usd: Optional[Decimal] = (
            Decimal(os.environ.get("CORTEX_LLM_MAX_COST_PER_INCIDENT_USD"))
            if os.environ.get("CORTEX_LLM_MAX_COST_PER_INCIDENT_USD")
            else None
        )

        # Model allowlist (empty = unrestricted)
        raw_allowed = os.environ.get("CORTEX_ALLOWED_MODELS", "")
        self.allowed_models: list[str] = (
            [m.strip() for m in raw_allowed.split(",") if m.strip()]
            if raw_allowed
            else []
        )

        # Adaptive routing
        self.enable_adaptive_routing: bool = (
            os.environ.get("ENABLE_ADAPTIVE_ROUTING", "0") == "1"
        )

        self._validate()

    def _validate(self) -> None:
        """Validate config at startup. Logs warnings; raises on critical mismatches."""
        paid = {"cheaperinference", "openai", "anthropic"}
        if not 1 <= self.timeout_seconds <= 120 or not 0 <= self.max_retries <= 3:
            raise ValueError("LLM timeout must be 1..120 seconds; retries must be 0..3")
        if not 16 <= self.max_output_tokens <= 4096 or not 1 <= self.max_requests_per_incident <= 12:
            raise ValueError("LLM token limit must be 16..4096; incident call limit must be 1..12")
        if any(p not in VALID_PROVIDERS for p in (self.diagnosis_provider, self.critique_provider, self.semantic_review_provider)):
            raise ValueError("invalid purpose-specific provider")
        if self.max_cost_per_incident_usd is not None and self.max_cost_per_incident_usd <= 0:
            raise ValueError("incident cost limit must be positive")

        # Warn if primary provider is paid but key is missing
        if self.provider in paid and not self.credential:
            logger.warning(
                "LLM provider %r is configured but credential is missing. "
                "Provider will be UNAVAILABLE.",
                self.provider,
            )

        # Detect cross-provider credential contamination
        if self.provider == "gemini" and self.credential:
            # CheaperInference keys typically start with "ci_" patterns
            # We can only warn — we cannot definitively parse foreign key formats
            base_url = os.environ.get("OPENAI_BASE_URL", "")
            if "cheaperinference.com" in base_url:
                logger.warning(
                    "LLM_PROVIDER=gemini but OPENAI_BASE_URL points to CheaperInference. "
                    "Set LLM_PROVIDER=cheaperinference to avoid credential confusion."
                )

        # Warn if paid fallback is enabled explicitly
        if self.allow_paid_llm_fallback:
            logger.info(
                "ALLOW_PAID_LLM_FALLBACK=true — paid providers may be called "
                "when primary is unavailable."
            )

    @property
    def active_model(self) -> str:
        """Return the model name for the current provider."""
        return {
            "nvidia": self.nvidia_model,
            "gemini": self.gemini_model,
            "cheaperinference": self.cheaperinference_model,
            "openai": self.openai_model,
            "anthropic": self.anthropic_model,
            "ollama": self.ollama_model,
            "heuristic": "cortex-heuristic-reasoner",
        }.get(self.provider, "cortex-heuristic-reasoner")

    @property
    def credential_present(self) -> bool:
        return bool(self.credential)

    def safe_dict(self) -> dict:
        """Return a settings dict safe for logging/API responses — no secrets."""
        return {
            "provider": self.provider,
            "model": self.active_model,
            "fallback_providers": self.fallback_providers,
            "allow_paid_llm_fallback": self.allow_paid_llm_fallback,
            "credential_present": self.credential_present,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "max_output_tokens": self.max_output_tokens,
            "max_requests_per_incident": self.max_requests_per_incident,
        }


# ---------------------------------------------------------------------------
# CORTEX-wide settings
# ---------------------------------------------------------------------------
class CortexSettings:
    """Top-level application settings."""

    def __init__(self) -> None:
        self.llm: LLMSettings = LLMSettings()
        self.cors_origins: list[str] = os.environ.get(
            "CORTEX_CORS_ORIGINS",
            "http://localhost:3100,http://127.0.0.1:3100",
        ).split(",")
        self.data_dir: Path = Path(
            os.environ.get("CORTEX_DATA_DIR", str(_BACKEND_DIR / "data"))
        )
        # Public URL of this CORTEX instance — NOT a provider URL
        self.app_url: str = os.environ.get("APP_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere
# ---------------------------------------------------------------------------
settings = CortexSettings()
