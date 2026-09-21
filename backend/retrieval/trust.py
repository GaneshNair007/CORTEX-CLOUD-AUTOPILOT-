"""Knowledge reliability and historical remediation success are separate signals."""
from typing import Any
from .config import RetrievalConfig


def trust_scores(metadata: dict[str, Any], config: RetrievalConfig) -> tuple[float, float]:
    if not metadata.get("verified"):
        return config.trust_weights.get("UNVERIFIED", .1), config.outcome_weights.get("UNVERIFIED", .1)
    if metadata.get("document_type") == "runbook":
        return 1., 1.
    status = metadata.get("memory_status", "UNVERIFIED")
    return config.trust_weights.get(status, .1), config.outcome_weights.get(status, .1)
