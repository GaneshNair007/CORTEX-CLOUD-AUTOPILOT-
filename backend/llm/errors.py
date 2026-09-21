"""
CORTEX LLM — Normalized error taxonomy.

All provider-specific exceptions are caught internally and re-raised as
one of these typed errors. Raw upstream error messages are NEVER surfaced
to API callers or logged at INFO level (only DEBUG/sanitized).
"""

from __future__ import annotations


class LLMError(RuntimeError):
    """Base class for all LLM errors."""

    error_code: str = "UNKNOWN_PROVIDER_ERROR"

    def __init__(self, message: str, *, provider: str = "unknown") -> None:
        super().__init__(message)
        self.provider = provider

    def to_api_dict(self) -> dict:
        return {
            "error": {
                "code": self.error_code,
                "provider": self.provider,
            }
        }


class AuthenticationError(LLMError):
    """Provider returned 401 / invalid credential. Do NOT retry."""

    error_code = "AUTHENTICATION_ERROR"


class RateLimitedError(LLMError):
    """Provider returned 429. Retry with backoff or fallback."""

    error_code = "RATE_LIMITED"

    def __init__(self, message: str, *, provider: str = "unknown", retry_after_s: float | None = None) -> None:
        super().__init__(message, provider=provider)
        self.retry_after_s = retry_after_s


class QuotaExhaustedError(LLMError):
    """Free-tier quota used up. Fallback or wait until reset."""

    error_code = "QUOTA_EXHAUSTED"


class InsufficientBalanceError(LLMError):
    """Paid provider wallet is empty. Do NOT retry."""

    error_code = "INSUFFICIENT_BALANCE"


class ModelUnavailableError(LLMError):
    """Requested model not available on this provider."""

    error_code = "MODEL_UNAVAILABLE"


class ProviderTimeoutError(LLMError):
    """Request timed out. Retry is permitted."""

    error_code = "TIMEOUT"


class ProviderUnavailableError(LLMError):
    """Provider returned 5xx or is unreachable."""

    error_code = "PROVIDER_UNAVAILABLE"


class InvalidRequestError(LLMError):
    """Bad request parameters. Do NOT retry unchanged."""

    error_code = "INVALID_REQUEST"


class MalformedResponseError(LLMError):
    """Provider returned an unparseable response."""

    error_code = "MALFORMED_RESPONSE"


class LLMBudgetExhaustedError(LLMError):
    """Per-incident LLM call budget exceeded."""

    error_code = "LLM_BUDGET_EXHAUSTED"


class ConfigurationError(LLMError):
    """Provider is misconfigured (e.g., wrong key family). Do NOT call network."""

    error_code = "CONFIGURATION_ERROR"


# ---------------------------------------------------------------------------
# HTTP status → error class mapping (for OpenAI-compatible providers)
# ---------------------------------------------------------------------------
RETRYABLE_CODES = {429, 500, 502, 503, 504}
NON_RETRYABLE_CODES = {400, 401, 403, 404, 422}


def classify_http_error(status: int, body: str, provider: str) -> LLMError:
    """Map an HTTP error status to the correct typed exception."""
    body_lower = body.lower()
    if status == 401:
        return AuthenticationError(f"HTTP 401 from {provider}", provider=provider)
    if status == 403:
        if "balance" in body_lower or "insufficient" in body_lower:
            return InsufficientBalanceError(
                f"Insufficient balance on {provider}", provider=provider
            )
        return AuthenticationError(
            f"HTTP 403 from {provider} — permission denied", provider=provider
        )
    if status == 429:
        if "quota" in body_lower or "exhausted" in body_lower:
            return QuotaExhaustedError(
                f"Quota exhausted on {provider}", provider=provider
            )
        return RateLimitedError(f"HTTP 429 from {provider}", provider=provider)
    if status == 404:
        return ModelUnavailableError(
            f"Model not found on {provider}", provider=provider
        )
    if status in (500, 502, 503, 504):
        return ProviderUnavailableError(
            f"HTTP {status} from {provider}", provider=provider
        )
    if status in (400, 422):
        return InvalidRequestError(
            f"HTTP {status} from {provider} — bad request", provider=provider
        )
    return LLMError(f"HTTP {status} from {provider}", provider=provider)
