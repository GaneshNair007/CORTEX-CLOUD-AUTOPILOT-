"""
CORTEX Cloud Autopilot — Docker Cloud Provider
Uses the official Docker Python SDK to manage containers when Docker daemon is available.
Docker is explicit opt-in. Unavailable/unsupported operations fail without a sandbox fallback.
"""

from typing import Dict, Any, List, Optional
import time
from backend.providers.base import CloudProvider
from backend.providers.sandbox_provider import LocalSandboxProvider

try:
    import docker
    from docker.errors import DockerException
except ImportError:
    docker = None
    DockerException = Exception


class DockerProvider(CloudProvider):
    """
    Docker Engine API Provider.
    Inspects, restarts, and manages Docker containers when daemon is running.
    """

    def __init__(self):

        self.client = None
        self.is_connected = False

        if docker is not None:
            try:
                self.client = docker.from_env()
                self.client.ping()
                self.is_connected = True
            except (DockerException, Exception):
                self.is_connected = False
                self.client = None

    def list_resources(self) -> List[Dict[str, Any]]:
        if not self.is_connected or not self.client:
            return []

        try:
            containers = self.client.containers.list(all=True)
            return [
                {
                    "service": c.name,
                    "id": c.id[:12],
                    "status": c.status,
                    "image": str(c.image),
                    "provider": "docker",
                }
                for c in containers
            ]
        except Exception:
            return []

    def get_resource_state(self, service: str) -> Dict[str, Any]:
        if not self.is_connected or not self.client:
            return {"service": service, "status": "UNKNOWN", "state_available": False, "provider": "docker"}

        try:
            c = self.client.containers.get(service)
            return {
                "service": service,
                "id": c.id[:12],
                "status": "UP" if c.status == "running" else "DOWN",
                "ready": c.status == "running",
                "replicas": 1,
                "created": c.attrs.get("Created"),
            }
        except Exception:
            return {"service": service, "status": "UNKNOWN", "state_available": False, "provider": "docker"}

    def get_metrics(self, service: str) -> Dict[str, Any]:
        # Always use sandbox HTTP metrics collector for application-level latency/RPS
        return {"service": service, "metrics_available": False, "source": "unavailable", "simulated": False}

    def restart_service(self, service: str) -> Dict[str, Any]:
        if not self.is_connected or not self.client:
            return {"status": "FAILED", "service": service, "error": "DOCKER_UNAVAILABLE_OR_RESTART_FAILED"}

        try:
            c = self.client.containers.get(service)
            c.restart(timeout=5)
            c.reload()
            return {
                "status": "SUCCESS" if c.status == "running" else "FAILED",
                "service": service,
                "container_id": c.id[:12],
                "action": "docker_restart",
                "timestamp": time.time(),
            }
        except Exception:
            return {"status": "FAILED", "service": service, "error": "DOCKER_UNAVAILABLE_OR_RESTART_FAILED"}

    def scale_service(self, service: str, replicas: int) -> Dict[str, Any]:
        # Docker standalone containers scale by replica process or sandbox manager
        return {"status": "FAILED", "error": "STANDALONE_DOCKER_SCALING_NOT_IMPLEMENTED"}

    def rollback_service(self, service: str, revision: Optional[str] = None) -> Dict[str, Any]:
        return {"status": "FAILED", "error": "DOCKER_ROLLBACK_NOT_IMPLEMENTED"}

    def health_check(self, service: str) -> Dict[str, Any]:
        if not self.is_connected or not self.client:
            return {"status": "UNKNOWN", "service": service, "error": "DOCKER_UNAVAILABLE"}

        try:
            c = self.client.containers.get(service)
            return {"status": "UP" if c.status == "running" else "DOWN", "service": service}
        except Exception:
            return {"status": "UNKNOWN", "service": service, "error": "DOCKER_UNAVAILABLE"}

    def estimate_cost(self, service: str, replicas: int) -> float:
        raise NotImplementedError("Docker billing estimation is not connected")
