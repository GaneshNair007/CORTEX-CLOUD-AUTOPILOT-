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
    rps: float = 0.0
    error_rate_pct: float = 0.0
    p50_latency_ms: float = 12.0
    p95_latency_ms: float = 45.0
    p99_latency_ms: float = 85.0
    cpu_percent: float = 15.0
    memory_percent: float = 20.0
    active_replicas: int = 1
    queue_depth: int = 0
    source: Literal["prometheus", "http_probe", "fallback"] = "http_probe"
    freshness: Literal["FRESH", "DEGRADED", "STALE"] = "FRESH"
    age_seconds: float = 0.0

    def compute_freshness(self) -> None:
        """Evaluates telemetry age against freshness thresholds."""
        self.age_seconds = round(time.time() - self.timestamp, 2)
        if self.age_seconds < 15.0:
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
    overall_status: Literal["OPTIMAL", "OBSERVABILITY_DEGRADED", "OFFLINE"] = "OPTIMAL"
    primary_available: bool = True
    secondary_available: bool = True
    active_services: int = 8
    effective_autonomy_ceiling: int = 3  # Level 0 (Read-only), 1 (Recommend), 2 (Guarded), 3 (Autonomous)
    reason: str = "All observability pipelines operational."
