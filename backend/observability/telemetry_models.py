"""
CORTEX Cloud Autopilot — Observability Telemetry Models
Defines multi-signal telemetry models with explicit freshness tracking.
"""

import time
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class ServiceTelemetry(BaseModel):
    """Point-in-time telemetry snapshot for a microservice."""
    service: str
    timestamp: float = Field(default_factory=time.time)
    # Optional observations: a failed scrape is not evidence of a healthy zero.
    # Numeric defaults retain the legacy constructor contract; collectors explicitly
    # pass None for every unobserved value.
    rps: Optional[float] = 0.0
    error_rate_pct: Optional[float] = 0.0
    p50_latency_ms: Optional[float] = 12.0
    p95_latency_ms: Optional[float] = 45.0
    p99_latency_ms: Optional[float] = 85.0
    cpu_percent: Optional[float] = 15.0
    memory_percent: Optional[float] = 20.0
    active_replicas: Optional[int] = 1
    queue_depth: Optional[int] = 0
    source: Literal["prometheus", "sandbox_model", "http_probe", "fallback"] = "http_probe"
    simulated: bool = False
    metrics_available: bool = False
    service_status: Literal["UP", "DOWN", "UNKNOWN"] = "UNKNOWN"
    warnings: list[str] = Field(default_factory=list)
    freshness: Literal["FRESH", "DEGRADED", "STALE"] = "FRESH"
    age_seconds: float = 0.0

    def compute_freshness(self) -> None:
        """Evaluates telemetry age against freshness thresholds."""
        age = time.time() - self.timestamp
        self.age_seconds = round(max(0.0, age), 2)
        if age < -5.0:
            self.freshness = "STALE"
        elif self.age_seconds < 15.0:
            self.freshness = "FRESH"
        elif self.age_seconds <= 60.0:
            self.freshness = "DEGRADED"
        else:
            self.freshness = "STALE"

    def model_post_init(self, __context: Any) -> None:
        self.compute_freshness()

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class ObservabilityStatus(BaseModel):
    """System-wide observability pipeline state and privilege ceiling."""
    overall_status: Literal["OPTIMAL", "OBSERVABILITY_DEGRADED", "OFFLINE"] = "OFFLINE"
    primary_available: bool = False
    secondary_available: bool = False
    active_services: int = 0
    effective_autonomy_ceiling: int = 0
    reason: str = "No fresh observability observations available."
    source: str = "unavailable"
    simulated: bool = False
