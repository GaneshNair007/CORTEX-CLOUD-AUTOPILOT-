"""First-class NVIDIA NIM adapter using its OpenAI-compatible chat endpoint."""
from urllib.parse import urlparse
from backend.llm.providers.openai import OpenAIProvider
from backend.llm.errors import ConfigurationError


class NvidiaNIMProvider(OpenAIProvider):
    name = "nvidia"
    # Hosted developer quota/billing is account-dependent; no paid fallback here.
    is_paid = False
    extra_payload = {"chat_template_kwargs": {"enable_thinking": False}}

    def __init__(self, api_key: str, model: str = "nvidia/nemotron-3.5-lightning-30b-a3b",
                 base_url: str = "https://integrate.api.nvidia.com/v1", timeout: float = 30):
        url = urlparse(base_url)
        if url.scheme != "https" or url.hostname != "integrate.api.nvidia.com" or url.username or url.password or url.query or url.fragment:
            raise ConfigurationError("NVIDIA hosted credentials require the official HTTPS API endpoint", provider=self.name)
        super().__init__(api_key=api_key, model=model, base_url=base_url, timeout=timeout)
