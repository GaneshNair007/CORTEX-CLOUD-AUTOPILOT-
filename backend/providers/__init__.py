from .base import CloudProvider
import os
from .sandbox_provider import LocalSandboxProvider
from .docker_provider import DockerProvider
from .cloud_placeholders import KubernetesProvider, AWSProvider, AzureProvider, GCPProvider

_active_provider: CloudProvider = None

def get_active_provider() -> CloudProvider:
    global _active_provider
    if _active_provider is None:
        name = os.environ.get("CORTEX_EXECUTION_PROVIDER", "local_sandbox")
        if name == "local_sandbox":
            _active_provider = LocalSandboxProvider()
        elif name == "docker":
            _active_provider = DockerProvider()
        else:
            raise ValueError("CORTEX_EXECUTION_PROVIDER must be local_sandbox or docker; cloud adapters are not implemented")
    return _active_provider

def set_active_provider(provider: CloudProvider) -> None:
    global _active_provider
    _active_provider = provider

__all__ = [
    "CloudProvider",
    "LocalSandboxProvider",
    "DockerProvider",
    "KubernetesProvider",
    "AWSProvider",
    "AzureProvider",
    "GCPProvider",
    "get_active_provider",
    "set_active_provider",
]
