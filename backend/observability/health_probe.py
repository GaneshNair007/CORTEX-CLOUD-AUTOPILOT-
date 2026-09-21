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

    @staticmethod
    def normalize_target(service: str) -> str:
        """Map public aliases to the actual registered local service."""
        return {"payment-api": "payment-service", "payments-api": "payment-service",
                "postgres-primary": "postgres", "redis-cache": "redis"}.get(service, service)

    def check_service(self, service: str) -> Dict[str, Any]:
        """Queries /health and /ready on the target service."""
        # Normalize naming
        norm = self.normalize_target(service)

        health = sandbox_manager.get_health(norm)
        is_up = health.get("status") == "UP"

        return {
            "service": service,
            "status": health.get("status") if health.get("status") in ("UP", "DOWN") else "UNKNOWN",
            "ready": health.get("ready") if is_up else False,
            "uptime_seconds": health.get("uptime_seconds"),
            "replicas": health.get("replicas"),
            "source": "secondary_http_probe",
            "simulated": True,
        }

    def check_all(self) -> Dict[str, Dict[str, Any]]:
        """Checks all registered sandbox services."""
        return {name: self.check_service(name) for name in sandbox_manager.specs}


health_probe = HealthProbe()
