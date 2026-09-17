from .base import CloudProvider
from .sandbox_provider import LocalSandboxProvider
from .docker_provider import DockerProvider
from .cloud_placeholders import KubernetesProvider, AWSProvider, AzureProvider, GCPProvider

_active_provider: CloudProvider = None

def get_active_provider() -> CloudProvider:
    global _active_provider
    if _active_provider is None:
        # Default to DockerProvider (which uses Docker if available or auto-falls back to LocalSandboxProvider)
        _active_provider = DockerProvider()
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
