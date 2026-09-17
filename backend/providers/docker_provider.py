"""
CORTEX Cloud Autopilot — Docker Cloud Provider
Uses the official Docker Python SDK to manage containers when Docker daemon is available.
Gracefully delegates to LocalSandboxProvider when Docker daemon is unreachable.
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
        self.fallback = LocalSandboxProvider()
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
            return self.fallback.list_resources()

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
            return self.fallback.list_resources()

    def get_resource_state(self, service: str) -> Dict[str, Any]:
        if not self.is_connected or not self.client:
            return self.fallback.get_resource_state(service)

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
            return self.fallback.get_resource_state(service)

    def get_metrics(self, service: str) -> Dict[str, Any]:
        # Always use sandbox HTTP metrics collector for application-level latency/RPS
        return self.fallback.get_metrics(service)

    def restart_service(self, service: str) -> Dict[str, Any]:
        if not self.is_connected or not self.client:
            return self.fallback.restart_service(service)

        try:
            c = self.client.containers.get(service)
            c.restart(timeout=5)
            return {
                "status": "SUCCESS",
                "service": service,
                "container_id": c.id[:12],
                "action": "docker_restart",
                "timestamp": time.time(),
            }
        except Exception:
            return self.fallback.restart_service(service)

    def scale_service(self, service: str, replicas: int) -> Dict[str, Any]:
        # Docker standalone containers scale by replica process or sandbox manager
        return self.fallback.scale_service(service, replicas)

    def rollback_service(self, service: str, revision: Optional[str] = None) -> Dict[str, Any]:
        return self.fallback.rollback_service(service, revision)

    def health_check(self, service: str) -> Dict[str, Any]:
        if not self.is_connected or not self.client:
            return self.fallback.health_check(service)

        try:
            c = self.client.containers.get(service)
            return {"status": "UP" if c.status == "running" else "DOWN", "service": service}
        except Exception:
            return self.fallback.health_check(service)

    def estimate_cost(self, service: str, replicas: int) -> float:
        return self.fallback.estimate_cost(service, replicas)
