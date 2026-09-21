"""Local HTTP state and recovery claims remain distinguishable from real cloud metrics."""
from unittest.mock import Mock
import httpx
from backend.observability.metrics_collector import MetricsCollector
from backend.providers.sandbox_provider import LocalSandboxProvider
from sandbox.manager import sandbox_manager


def test_sandbox_mutation_ports_require_manager_identity():
    port = sandbox_manager.specs["payment-service"]["port"]
    response = httpx.post(f"http://127.0.0.1:{port}/restart", trust_env=False)
    assert response.status_code == 401


def test_missing_metrics_are_unknown_not_healthy(monkeypatch):
    monkeypatch.setattr(sandbox_manager, "get_metrics", lambda _: {"metrics_available": False})
    monkeypatch.setattr(sandbox_manager, "get_health", lambda _: {"status": "UNKNOWN"})
    collector = MetricsCollector()
    result = collector.collect("payment-service")
    assert result.source == "http_probe" and result.p95_latency_ms is None
    assert result.error_rate_pct is None and not result.metrics_available
    assert collector.get_status().overall_status == "OFFLINE"


def test_real_http_model_metrics_have_explicit_provenance():
    result = MetricsCollector().collect("notification-worker")
    assert result.source == "sandbox_model" and result.simulated and result.metrics_available
    assert result.p95_latency_ms is not None


def test_rollback_restores_captured_state_after_provider_restart():
    provider = LocalSandboxProvider()
    before = provider.get_resource_state("notification-worker")
    result = provider.scale_service("notification-worker", 7)
    assert result["status"] == "SUCCESS"
    restarted_provider = LocalSandboxProvider()
    restored = restarted_provider.rollback_service("notification-worker")
    assert restored["status"] == "SUCCESS"
    after = restarted_provider.get_resource_state("notification-worker")
    assert after["replicas"] == before["replicas"]
    assert after["version"] != before["version"]
    assert restarted_provider.rollback_service("notification-worker")["status"] == "FAILED"


def test_failed_scale_cannot_claim_success(monkeypatch):
    provider = LocalSandboxProvider()
    monkeypatch.setattr(sandbox_manager, "scale_service", lambda *args: {"status": "FAILED"})
    result = provider.scale_service("auth-service", 4)
    assert result["status"] == "FAILED" and result["error"] == "SCALE_NOT_CONFIRMED"


def test_docker_failure_never_falls_back_to_sandbox(monkeypatch):
    from backend.providers.docker_provider import DockerProvider
    monkeypatch.setattr(sandbox_manager, "restart_service", Mock())
    provider = DockerProvider.__new__(DockerProvider)
    provider.client, provider.is_connected = None, False
    assert provider.restart_service("payment-service")["status"] == "FAILED"
    assert provider.scale_service("payment-service", 4)["status"] == "FAILED"
    sandbox_manager.restart_service.assert_not_called()
