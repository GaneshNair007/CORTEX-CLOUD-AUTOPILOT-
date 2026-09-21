"""Collect observed HTTP telemetry, keeping sandbox models and missing data explicit."""

import math
import threading
import time
from typing import Any

from backend.observability.telemetry_models import ServiceTelemetry, ObservabilityStatus
from backend.observability.health_probe import health_probe
from sandbox.manager import sandbox_manager


def _number(value: Any) -> float | None:
    """Accept only finite, nonnegative observations, including an observed zero."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed >= 0 else None


class MetricsCollector:
    """Cache bounded service observations without claiming unprobed dependencies work."""

    def __init__(self) -> None:
        self.cached_snapshots: dict[str, ServiceTelemetry] = {}
        self.primary_enabled = True
        self._lock = threading.RLock()

    def set_primary_available(self, available: bool) -> None:
        """Enable/disable the sandbox metrics path for an explicit lab experiment."""
        with self._lock:
            self.primary_enabled = available

    def get_status(self) -> ObservabilityStatus:
        """Summarize real observations; an enabled scraper alone proves nothing."""
        with self._lock:
            snapshots = [value.model_copy(deep=True) for value in self.cached_snapshots.values()]
        for value in snapshots:
            value.compute_freshness()
        fresh = [value for value in snapshots if value.freshness == "FRESH"]
        primary = self.primary_enabled and any(value.metrics_available for value in fresh)
        secondary = any(value.service_status != "UNKNOWN" for value in fresh)
        active = sum(value.service_status == "UP" for value in fresh)
        complete = len(fresh) == len(sandbox_manager.specs) and all(value.metrics_available for value in fresh)
        optimal = primary and complete
        return ObservabilityStatus(
            overall_status="OPTIMAL" if optimal else "OBSERVABILITY_DEGRADED" if primary or secondary else "OFFLINE",
            primary_available=primary,
            secondary_available=secondary,
            active_services=active,
            effective_autonomy_ceiling=3 if optimal else 1 if primary or secondary else 0,
            reason=("Fresh local sandbox model observations available for all registered services."
                    if optimal else "Telemetry is incomplete or stale; health probes do not establish SLO recovery."
                    if primary or secondary else "No fresh telemetry available; infrastructure health is unknown."),
            source="sandbox_model" if primary else "http_probe" if secondary else "unavailable",
            simulated=bool(primary),
        )

    def collect(self, service: str) -> ServiceTelemetry:
        """Read sandbox workload models over HTTP; never invent missing SLO values."""
        norm = health_probe.normalize_target(service)
        raw = sandbox_manager.get_metrics(norm) if self.primary_enabled else {}
        available = raw.get("metrics_available") is True
        if available:
            timestamp = _number(raw.get("timestamp"))
            p95 = _number(raw.get("p95_latency_ms"))
            error_rate = _number(raw.get("error_rate_pct"))
            replicas = _number(raw.get("replicas"))
            telemetry = ServiceTelemetry(
                service=service, timestamp=timestamp if timestamp is not None else 0.0,
                rps=_number(raw.get("rps")), error_rate_pct=error_rate,
                p50_latency_ms=_number(raw.get("p50_latency_ms")), p95_latency_ms=p95,
                p99_latency_ms=_number(raw.get("p99_latency_ms")),
                cpu_percent=_number(raw.get("cpu_percent")), memory_percent=_number(raw.get("memory_percent")),
                active_replicas=int(replicas) if replicas is not None and replicas.is_integer() else None,
                queue_depth=None, source="sandbox_model", simulated=True,
                metrics_available=timestamp is not None and p95 is not None and error_rate is not None,
                service_status=raw.get("status") if raw.get("status") in ("UP", "DOWN") else "UNKNOWN",
                warnings=["Latency, error percentage and replicas are local sandbox model values; no cloud workload is measured."],
            )
        else:
            probe = health_probe.check_service(service)
            telemetry = ServiceTelemetry(
                service=service, timestamp=time.time(), rps=None, error_rate_pct=None,
                p50_latency_ms=None, p95_latency_ms=None, p99_latency_ms=None,
                cpu_percent=None, memory_percent=None, active_replicas=probe.get("replicas"),
                queue_depth=None, source="http_probe", metrics_available=False,
                service_status=probe["status"], simulated=True,
                warnings=["Primary metrics unavailable; an HTTP liveness probe cannot determine latency, error rate or recovery."],
            )
        telemetry.compute_freshness()
        if telemetry.freshness != "FRESH":
            telemetry.warnings.append("Telemetry is stale or timestamp is invalid; do not use it to verify recovery.")
        with self._lock:
            if norm in sandbox_manager.specs:
                self.cached_snapshots[norm] = telemetry.model_copy(deep=True)
        return telemetry

    def collect_all(self) -> dict[str, ServiceTelemetry]:
        """Collect the configured local lab, retaining the public payment alias."""
        services = ["payment-api" if name == "payment-service" else name for name in sandbox_manager.specs]
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as pool:
            return dict(zip(services, pool.map(self.collect, services)))


metrics_collector = MetricsCollector()
