"""
CORTEX Cloud Autopilot — Chaos Engineering Engine Tests
"""

import pytest
from backend.chaos.engine import chaos_engine


def test_chaos_safety_violation_production():
    with pytest.raises(PermissionError) as exc_info:
        chaos_engine.inject_fault("payment-service", "crash", environment="production")
    assert "SAFETY INVARIANT VIOLATION" in str(exc_info.value)


def test_chaos_safety_violation_staging():
    with pytest.raises(PermissionError) as exc_info:
        chaos_engine.inject_fault("auth-service", "cpu_stress", environment="staging")
    assert "SAFETY INVARIANT VIOLATION" in str(exc_info.value)


def test_chaos_experiment_lifecycle_sandbox():
    from backend.observability.metrics_collector import metrics_collector
    metrics_collector.collect_all()
    res = chaos_engine.inject_fault("payment-service", "latency", duration_sec=5, intensity=50.0, environment="sandbox")
    assert res["status"] == "ACTIVE"
    assert "experiment_id" in res
    assert res["target_service"] == "payment-service"

    active = chaos_engine.list_active_experiments()
    assert len(active) >= 1
    assert any(e["experiment_id"] == res["experiment_id"] for e in active)

    # Clear faults
    clear_res = chaos_engine.clear_faults("payment-service", environment="sandbox")
    assert clear_res["status"] == "CLEARED"
