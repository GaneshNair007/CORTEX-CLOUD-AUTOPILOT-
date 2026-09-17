"""
CORTEX Cloud Autopilot — Service Level Objective (SLO) Configuration & Budget Engine
Defines mathematical reliability targets and calculates real error budget burn rates.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class SLOTarget(BaseModel):
    service: str
    max_error_rate: float = Field(0.01, description="Maximum allowable HTTP error rate fraction (e.g. 0.01 = 1%)")
    max_p95_ms: float = Field(200.0, description="Maximum allowable 95th percentile response latency in milliseconds")
    min_availability: float = Field(0.999, description="Target availability percentage (e.g. 99.9%)")
    window_minutes: int = Field(60, description="Rolling evaluation window in minutes")


# Standard production-grade SLO targets for each microservice
SERVICE_SLOS: Dict[str, SLOTarget] = {
    "api-gateway": SLOTarget(service="api-gateway", max_error_rate=0.005, max_p95_ms=120.0, min_availability=0.9995),
    "auth-service": SLOTarget(service="auth-service", max_error_rate=0.005, max_p95_ms=80.0, min_availability=0.9995),
    "payment-service": SLOTarget(service="payment-service", max_error_rate=0.010, max_p95_ms=200.0, min_availability=0.9990),
    "payment-api": SLOTarget(service="payment-service", max_error_rate=0.010, max_p95_ms=200.0, min_availability=0.9990),
    "order-service": SLOTarget(service="order-service", max_error_rate=0.015, max_p95_ms=250.0, min_availability=0.9950),
    "inventory-service": SLOTarget(service="inventory-service", max_error_rate=0.020, max_p95_ms=180.0, min_availability=0.9950),
    "notification-worker": SLOTarget(service="notification-worker", max_error_rate=0.030, max_p95_ms=500.0, min_availability=0.9900),
    "redis": SLOTarget(service="redis", max_error_rate=0.001, max_p95_ms=15.0, min_availability=0.9999),
    "postgres": SLOTarget(service="postgres", max_error_rate=0.002, max_p95_ms=50.0, min_availability=0.9995),
    "postgres-primary": SLOTarget(service="postgres-primary", max_error_rate=0.002, max_p95_ms=50.0, min_availability=0.9995),
}

DEFAULT_SLO = SLOTarget(service="default", max_error_rate=0.01, max_p95_ms=200.0, min_availability=0.999)


def get_slo_for_service(service_name: str) -> SLOTarget:
    """Returns the configured SLO target for a service, or default."""
    norm = service_name.lower().replace("_", "-")
    return SERVICE_SLOS.get(norm, DEFAULT_SLO)


def calculate_burn_rate(observed_error_rate: float, slo: SLOTarget) -> float:
    """
    Computes real error budget burn rate:
      Burn Rate = Observed Error Rate / Maximum Allowable Error Rate
      - 1.0: Depleting budget at exactly the planned rate over the window
      - 14.4: 1-hour fast burn (depleting 2% of 30-day budget in 1 hour)
      - 6.0: 6-hour medium burn (depleting 5% of 30-day budget in 6 hours)
    """
    if slo.max_error_rate <= 0:
        return 1.0
    return round(observed_error_rate / slo.max_error_rate, 2)


def calculate_error_budget_remaining(
    total_requests: int,
    error_count: int,
    slo: SLOTarget
) -> Dict[str, Any]:
    """
    Computes remaining error budget percentage and status.
    """
    if total_requests <= 0:
        return {
            "budget_remaining_pct": 100.0,
            "status": "HEALTHY",
            "allowed_errors": 0,
            "actual_errors": 0
        }

    allowed_errors = int(total_requests * slo.max_error_rate)
    remaining_errors = max(0, allowed_errors - error_count)
    budget_pct = (remaining_errors / max(1, allowed_errors)) * 100.0 if allowed_errors > 0 else 100.0

    status = "HEALTHY"
    if budget_pct <= 0:
        status = "EXHAUSTED"
    elif budget_pct < 20:
        status = "CRITICAL"
    elif budget_pct < 50:
        status = "WARNING"

    return {
        "budget_remaining_pct": round(budget_pct, 1),
        "status": status,
        "allowed_errors": allowed_errors,
        "actual_errors": error_count,
        "burn_rate": calculate_burn_rate(error_count / max(1, total_requests), slo)
    }
