"""
CORTEX Cloud Autopilot — Cloud Provider Base Abstraction
Defines the standard contract for infrastructure actuators.
All mutating and telemetry actions must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class CloudProvider(ABC):
    """Abstract Base Class for all infrastructure providers."""

    @abstractmethod
    def list_resources(self) -> List[Dict[str, Any]]:
        """List all resources monitored and managed by this provider."""
        pass

    @abstractmethod
    def get_resource_state(self, service: str) -> Dict[str, Any]:
        """Fetch the current operational state of a resource."""
        pass

    @abstractmethod
    def get_metrics(self, service: str) -> Dict[str, Any]:
        """Fetch real-time metrics for the service (RPS, latency, error rate, CPU, memory)."""
        pass

    @abstractmethod
    def restart_service(self, service: str) -> Dict[str, Any]:
        """Restart the specified service or container."""
        pass

    @abstractmethod
    def scale_service(self, service: str, replicas: int) -> Dict[str, Any]:
        """Scale the specified service to the target replica count."""
        pass

    @abstractmethod
    def rollback_service(self, service: str, revision: Optional[str] = None) -> Dict[str, Any]:
        """Rollback the specified service to its previous stable revision."""
        pass

    @abstractmethod
    def health_check(self, service: str) -> Dict[str, Any]:
        """Check liveness and readiness of the service."""
        pass

    @abstractmethod
    def estimate_cost(self, service: str, replicas: int) -> float:
        """Estimate hourly cost in USD for this service configuration."""
        pass
