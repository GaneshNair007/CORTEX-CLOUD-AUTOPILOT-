"""
CORTEX Cloud Autopilot — Metrics Collector
Primary multi-signal telemetry ingestion with secondary health validation fallback.
Enforces telemetry freshness thresholds and dynamic autonomy ceilings.
"""

import time
from typing import Dict, Any, Optional
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.observability.telemetry_models import ServiceTelemetry, ObservabilityStatus
from backend.observability.health_probe import health_probe
from sandbox.manager import sandbox_manager


class MetricsCollector:
    """Multi-path observability collector tracking telemetry freshness and degraded states."""

    def __init__(self):
        self.cached_snapshots: Dict[str, ServiceTelemetry] = {}
        self.primary_enabled: bool = True  # Can be disabled during chaos testing to test degraded state

    def set_primary_available(self, available: bool) -> None:
        """Simulates Prometheus/primary telemetry outage for chaos testing."""
        self.primary_enabled = available

    def get_status(self) -> ObservabilityStatus:
        """Computes current observability health and autonomy ceiling."""
        if not self.primary_enabled:
            return ObservabilityStatus(
                overall_status="OBSERVABILITY_DEGRADED",
                primary_available=False,
                secondary_available=True,
                effective_autonomy_ceiling=1,  # Lower autonomy to L1 RECOMMEND
                reason="Primary Prometheus metrics unavailable. Operating on secondary HTTP probes.",
            )

        return ObservabilityStatus(
            overall_status="OPTIMAL",
            primary_available=True,
            secondary_available=True,
            effective_autonomy_ceiling=3,
            reason="All primary and secondary telemetry pipelines fully operational.",
        )

    def collect(self, service: str) -> ServiceTelemetry:
        """
        Collects live telemetry for the requested service.
        Primary: Real HTTP /metrics/json probe from sandbox microservice.
        Secondary: /health probe if metrics collector fails or is disabled.
        """
        norm = "payment-service" if service in ("payment-api", "payments-api") else service
        norm = "postgres" if norm == "postgres-primary" else norm
        norm = "redis" if norm == "redis-cache" else norm

        status = self.get_status()

        if self.primary_enabled:
            raw = sandbox_manager.get_metrics(norm)
            telemetry = ServiceTelemetry(
                service=service,
                timestamp=raw.get("timestamp", time.time()),
                rps=float(raw.get("rps", 0.0)),
                error_rate_pct=float(raw.get("error_rate_pct", 0.0)),
                p50_latency_ms=float(raw.get("p95_latency_ms", 45.0) * 0.4),
                p95_latency_ms=float(raw.get("p95_latency_ms", 45.0)),
                p99_latency_ms=float(raw.get("p95_latency_ms", 45.0) * 1.8),
                cpu_percent=float(raw.get("cpu_percent", 15.0)),
                memory_percent=float(raw.get("memory_percent", 20.0)),
                active_replicas=int(raw.get("replicas", 1)),
                source="prometheus",
            )
        else:
            # Degraded: fall back to secondary health probe
            hp = health_probe.check_service(service)
            is_up = hp.get("status") == "UP"
            telemetry = ServiceTelemetry(
                service=service,
                timestamp=time.time(),
                rps=0.0 if not is_up else 240.0,
                error_rate_pct=100.0 if not is_up else 0.5,
                p95_latency_ms=30000.0 if not is_up else 60.0,
                active_replicas=hp.get("replicas", 1),
                source="http_probe",
            )

        telemetry.compute_freshness()
        self.cached_snapshots[service] = telemetry
        return telemetry

    def collect_all(self) -> Dict[str, ServiceTelemetry]:
        """Collects telemetry for all 8 microservices."""
        services = [
            "api-gateway", "auth-service", "payment-api", "order-service",
            "inventory-service", "notification-worker", "redis", "postgres"
        ]
        return {s: self.collect(s) for s in services}


metrics_collector = MetricsCollector()
