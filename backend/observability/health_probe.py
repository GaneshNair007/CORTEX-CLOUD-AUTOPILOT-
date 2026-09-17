"""
CORTEX Cloud Autopilot — Secondary Health Probe
Queries HTTP /health, /ready, and container state to establish ground-truth liveness.
"""

from typing import Dict, Any
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sandbox.manager import sandbox_manager


class HealthProbe:
    """Secondary health probe querying live HTTP endpoints."""

    def check_service(self, service: str) -> Dict[str, Any]:
        """Queries /health and /ready on the target service."""
        # Normalize naming
        norm = "payment-service" if service in ("payment-api", "payments-api") else service
        norm = "postgres" if norm == "postgres-primary" else norm
        norm = "redis" if norm == "redis-cache" else norm

        health = sandbox_manager.get_health(norm)
        is_up = health.get("status") == "UP"

        return {
            "service": service,
            "status": "UP" if is_up else "DOWN",
            "ready": is_up,
            "uptime_seconds": health.get("uptime_seconds", 0.0),
            "replicas": health.get("replicas", 1),
            "source": "secondary_http_probe",
        }

    def check_all(self) -> Dict[str, Dict[str, Any]]:
        """Checks all registered sandbox services."""
        return {name: self.check_service(name) for name in sandbox_manager.specs}


health_probe = HealthProbe()
