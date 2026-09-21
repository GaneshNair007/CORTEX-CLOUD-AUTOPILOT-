"""NVIDIA routing uses fake test credentials and mocked HTTP, never a live key."""
import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock
import pytest

from backend.llm.providers.nvidia import NvidiaNIMProvider
from backend.llm.errors import AuthenticationError, RateLimitedError, ProviderTimeoutError
from backend.llm.telemetry import LLMCallBudget


def response(content="CORTEX_OK"):
    mock = MagicMock()
    mock.__enter__.return_value = mock
    mock.read.return_value = json.dumps({"choices": [{"message": {"content": content, "reasoning_content": "HIDDEN_TRACE"}}],
                                         "usage": {"prompt_tokens": 7, "completion_tokens": 3}}).encode()
    return mock


def test_nvidia_identity_payload_and_no_hidden_trace(monkeypatch, caplog):
    calls = []
    def urlopen(req, timeout):
        calls.append(req)
        return response()
    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    provider = NvidiaNIMProvider(api_key="FAKE_NVIDIA_ONLY")
    result = provider.generate("Reply exactly CORTEX_OK", max_tokens=32)
    assert result.provider == result.gateway == result.model_provider == "nvidia"
    assert result.text == "CORTEX_OK"
    assert "HIDDEN_TRACE" not in str(result.to_dict())
    payload = json.loads(calls[0].data)
    assert payload["stream"] is False
    assert payload["max_tokens"] == 32
    assert payload["chat_template_kwargs"]["enable_thinking"] is False
    assert calls[0].get_header("Authorization") == "Bearer FAKE_NVIDIA_ONLY"
    assert "FAKE_NVIDIA_ONLY" not in caplog.text


def test_nvidia_never_uses_gemini_credentials(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "FAKE_GOOGLE_KEY")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    from backend.llm.client import _build_provider
    assert _build_provider("nvidia") is None
    monkeypatch.setenv("NVIDIA_API_KEY", "FAKE_NVIDIA_KEY")
    assert _build_provider("nvidia")._api_key == "FAKE_NVIDIA_KEY"


@pytest.mark.parametrize("code,error", [(401, AuthenticationError), (429, RateLimitedError)])
def test_nvidia_typed_http_errors(monkeypatch, code, error):
    def fail(*args, **kwargs):
        raise urllib.error.HTTPError("https://integrate.api.nvidia.com", code, "error", {}, BytesIO(b'{}'))
    monkeypatch.setattr("urllib.request.urlopen", fail)
    with pytest.raises(error):
        NvidiaNIMProvider(api_key="FAKE_NVIDIA_KEY").generate("test")


def test_nvidia_timeout(monkeypatch):
    def fail(*args, **kwargs):
        raise TimeoutError()
    monkeypatch.setattr("urllib.request.urlopen", fail)
    with pytest.raises(ProviderTimeoutError):
        NvidiaNIMProvider(api_key="FAKE_NVIDIA_KEY").generate("test")


def test_atomic_call_budget_includes_concurrent_attempts():
    from concurrent.futures import ThreadPoolExecutor
    budget = LLMCallBudget(max_calls=3)
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(lambda _: budget.reserve("same-incident"), range(20))) == 3


def test_provider_key_redacted_before_network(monkeypatch):
    from backend.llm.sanitizer import sanitize_prompt
    value = "nvapi-" + "FAKE_TEST_SECRET" * 3
    prompt, _ = sanitize_prompt("The log contained " + value)
    assert value not in prompt and "REDACTED" in prompt


def test_purpose_routing_changes_actual_request(monkeypatch):
    from backend.llm import client as module
    from backend.config.settings import LLMSettings
    from backend.llm.health import LLMHealthMonitor
    monkeypatch.setattr(module, "llm_health_monitor", LLMHealthMonitor())
    monkeypatch.setattr(module, "llm_call_budget", LLMCallBudget(max_calls=4))
    monkeypatch.setenv("LLM_PRIMARY_PROVIDER", "nvidia")
    monkeypatch.setenv("NVIDIA_API_KEY", "FAKE_NVIDIA_KEY")
    monkeypatch.setenv("GEMINI_API_KEY", "FAKE_GEMINI_KEY")
    monkeypatch.setenv("CRITIQUE_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDERS", "heuristic")
    monkeypatch.setattr(module.settings, "llm", LLMSettings())
    requested = []
    def urlopen(req, timeout):
        requested.append(req.full_url)
        if "googleapis" in req.full_url:
            mock = response()
            mock.read.return_value = json.dumps({"candidates": [{"content": {"parts": [{"text": "critique"}]}}]}).encode()
            return mock
        return response()
    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    client = module.LLMClient()
    first = client.generate("diagnose", incident_id="PURPOSE-TEST", purpose="diagnosis")
    second = client.generate("critique", incident_id="PURPOSE-TEST", purpose="critique")
    assert first["provider"] == "nvidia" and second["provider"] == "gemini"
    assert "nvidia.com" in requested[0] and "googleapis" in requested[1]
