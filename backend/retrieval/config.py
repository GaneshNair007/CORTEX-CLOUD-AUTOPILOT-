"""Validated, environment-driven retrieval policy. No request-scoped globals."""
from functools import lru_cache
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from .models import RetrievalOptions


class RetrievalConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RETRIEVAL_", extra="ignore", env_ignore_empty=True)
    top_k: int = Field(default=5, ge=1, le=20)
    candidate_k: int = Field(default=30, ge=1, le=200)
    max_age_days: int | None = Field(default=None, ge=1, le=36500)
    recency_half_life: float = Field(default=180, gt=0)
    runbook_half_life: float = Field(default=730, gt=0)
    high_confidence: float = Field(default=.82, ge=0, le=1)
    min_acceptable: float = Field(default=.70, ge=0, le=1)
    confident_count: int = Field(default=3, ge=1, le=20)
    min_semantic_relevance: float = Field(default=.28, ge=0, le=1)
    diversity_penalty: float = Field(default=.08, ge=0, le=1)
    weights: dict[str, float] = Field(default_factory=lambda: {
        "semantic": .35, "failure_mode": .15, "technology": .10,
        "error": .10, "service_dependency": .10, "lexical": .08,
        "trust_outcome": .07, "recency": .05,
    })
    trust_weights: dict[str, float] = Field(default_factory=lambda: {
        "VERIFIED_RECOVERED": 1., "PARTIALLY_RECOVERED": .85, "NO_CHANGE": .80,
        "WORSE": .90, "ROLLED_BACK": .85, "UNVERIFIED": .10,
        "PROPOSED": .05, "EXECUTED": .10, "BLOCKED": .20, "REJECTED": .15,
    })
    outcome_weights: dict[str, float] = Field(default_factory=lambda: {
        "VERIFIED_RECOVERED": 1., "PARTIALLY_RECOVERED": .70, "NO_CHANGE": .40,
        "WORSE": .15, "ROLLED_BACK": .30, "UNVERIFIED": .10,
        "PROPOSED": .05, "EXECUTED": .10, "BLOCKED": .10, "REJECTED": .05,
    })
    telemetry_thresholds: dict[str, list[float]] = Field(default_factory=lambda: {
        "cpu": [70, 90], "memory": [75, 90], "db_connections": [80, 95],
        "latency": [200, 500], "error_rate": [1, 5],
    })

    @model_validator(mode="after")
    def validate_policy(self):
        required = {"semantic", "failure_mode", "technology", "error", "service_dependency", "lexical", "trust_outcome", "recency"}
        if set(self.weights) != required or abs(sum(self.weights.values()) - 1) > .0001:
            raise ValueError("retrieval weights must contain all components and sum to 1")
        for values in (self.weights, self.trust_weights, self.outcome_weights):
            if any(not 0 <= v <= 1 for v in values.values()):
                raise ValueError("retrieval weights must be between 0 and 1")
        if self.candidate_k < self.top_k or self.min_acceptable > self.high_confidence:
            raise ValueError("invalid retrieval limits/confidence thresholds")
        if any(len(v) != 2 or v[0] < 0 or v[0] >= v[1] for v in self.telemetry_thresholds.values()):
            raise ValueError("telemetry thresholds require increasing [high, critical] values")
        return self

    def options(self) -> RetrievalOptions:
        return RetrievalOptions(top_k=self.top_k, candidate_k=self.candidate_k, max_age_days=self.max_age_days)


@lru_cache(maxsize=1)
def get_config() -> RetrievalConfig:
    return RetrievalConfig()
