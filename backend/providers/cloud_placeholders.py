"""
CORTEX Cloud Autopilot — Cloud Provider Placeholders
Explicitly marks unconfigured cloud adapters as NOT_CONNECTED.
Rule: Never fake "connected" cloud providers.
"""

from typing import Dict, Any, List, Optional
from backend.providers.base import CloudProvider


class KubernetesProvider(CloudProvider):
    """Kubernetes cluster provider (K8s API client)."""
    def __init__(self, kubeconfig_path: Optional[str] = None):
        self.kubeconfig_path = kubeconfig_path
        self.is_connected = False

    def list_resources(self) -> List[Dict[str, Any]]:
        return [{"provider": "kubernetes", "status": "NOT_CONNECTED", "message": "Kubeconfig not configured"}]

    def get_resource_state(self, service: str) -> Dict[str, Any]:
        return {"service": service, "provider": "kubernetes", "status": "NOT_CONNECTED"}

    def get_metrics(self, service: str) -> Dict[str, Any]:
        raise NotImplementedError("Kubernetes metrics-server not connected in local environment.")

    def restart_service(self, service: str) -> Dict[str, Any]:
        raise NotImplementedError("Kubernetes provider not connected.")

    def scale_service(self, service: str, replicas: int) -> Dict[str, Any]:
        raise NotImplementedError("Kubernetes provider not connected.")

    def rollback_service(self, service: str, revision: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("Kubernetes provider not connected.")

    def health_check(self, service: str) -> Dict[str, Any]:
        return {"status": "NOT_CONNECTED", "provider": "kubernetes"}

    def estimate_cost(self, service: str, replicas: int) -> float:
        return 0.0


class AWSProvider(CloudProvider):
    """AWS Cloud Provider (EC2, ECS, EKS, RDS). Placeholder."""
    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.is_connected = False

    def list_resources(self) -> List[Dict[str, Any]]:
        return [{"provider": "aws", "region": self.region, "status": "NOT_CONNECTED"}]

    def get_resource_state(self, service: str) -> Dict[str, Any]:
        return {"service": service, "provider": "aws", "status": "NOT_CONNECTED"}

    def get_metrics(self, service: str) -> Dict[str, Any]:
        raise NotImplementedError("AWS CloudWatch not connected. Credentials required.")

    def restart_service(self, service: str) -> Dict[str, Any]:
        raise NotImplementedError("AWS provider not connected.")

    def scale_service(self, service: str, replicas: int) -> Dict[str, Any]:
        raise NotImplementedError("AWS provider not connected.")

    def rollback_service(self, service: str, revision: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("AWS provider not connected.")

    def health_check(self, service: str) -> Dict[str, Any]:
        return {"status": "NOT_CONNECTED", "provider": "aws"}

    def estimate_cost(self, service: str, replicas: int) -> float:
        return 0.0


class AzureProvider(CloudProvider):
    """Azure Cloud Provider (AKS, VMSS). Placeholder."""
    def list_resources(self) -> List[Dict[str, Any]]:
        return [{"provider": "azure", "status": "NOT_CONNECTED"}]

    def get_resource_state(self, service: str) -> Dict[str, Any]:
        return {"service": service, "provider": "azure", "status": "NOT_CONNECTED"}

    def get_metrics(self, service: str) -> Dict[str, Any]:
        raise NotImplementedError("Azure Monitor not connected.")

    def restart_service(self, service: str) -> Dict[str, Any]:
        raise NotImplementedError("Azure provider not connected.")

    def scale_service(self, service: str, replicas: int) -> Dict[str, Any]:
        raise NotImplementedError("Azure provider not connected.")

    def rollback_service(self, service: str, revision: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("Azure provider not connected.")

    def health_check(self, service: str) -> Dict[str, Any]:
        return {"status": "NOT_CONNECTED", "provider": "azure"}

    def estimate_cost(self, service: str, replicas: int) -> float:
        return 0.0


class GCPProvider(CloudProvider):
    """Google Cloud Provider (GKE, Cloud Run). Placeholder."""
    def list_resources(self) -> List[Dict[str, Any]]:
        return [{"provider": "gcp", "status": "NOT_CONNECTED"}]

    def get_resource_state(self, service: str) -> Dict[str, Any]:
        return {"service": service, "provider": "gcp", "status": "NOT_CONNECTED"}

    def get_metrics(self, service: str) -> Dict[str, Any]:
        raise NotImplementedError("GCP Cloud Monitoring not connected.")

    def restart_service(self, service: str) -> Dict[str, Any]:
        raise NotImplementedError("GCP provider not connected.")

    def scale_service(self, service: str, replicas: int) -> Dict[str, Any]:
        raise NotImplementedError("GCP provider not connected.")

    def rollback_service(self, service: str, revision: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("GCP provider not connected.")

    def health_check(self, service: str) -> Dict[str, Any]:
        return {"status": "NOT_CONNECTED", "provider": "gcp"}

    def estimate_cost(self, service: str, replicas: int) -> float:
        return 0.0
