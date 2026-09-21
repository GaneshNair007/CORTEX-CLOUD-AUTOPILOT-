"""
CORTEX LLM — Abstract base provider contract.

Every concrete provider must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from backend.llm.telemetry import LLMResponse


class BaseLLMProvider(ABC):
    """Common contract for all LLM provider implementations."""

    #: Canonical provider name (matches LLM_PROVIDER values)
    name: str = "unknown"

    #: Whether calls to this provider incur monetary cost
    is_paid: bool = False

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        model: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate a completion.

        Args:
            prompt:      The user prompt text (already sanitized).
            system:      Optional system instruction (already sanitized).
            temperature: Sampling temperature.
            max_tokens:  Maximum output tokens.
            model:       Override the configured model for this call.

        Returns:
            LLMResponse with text and observability metadata.

        Raises:
            LLMError subclass on any failure.
        """

    def health_check(self) -> dict:
        """
        Non-billable health check.
        Returns dict with at least: {"status": "HEALTHY"|"DEGRADED"|"UNAVAILABLE"|"UNKNOWN"}
        Default implementation: reports UNKNOWN (override in providers that
        have a metadata endpoint).
        """
        return {"status": "UNKNOWN", "provider": self.name}

    @property
    def metadata(self) -> dict:
        """Safe provider metadata for API/UI consumption. Never include credentials."""
        return {
            "provider": self.name,
            "is_paid": self.is_paid,
        }
