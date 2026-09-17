"""
CORTEX Cloud Autopilot — 15 Absolute System Invariant Tests
Verifies the non-negotiable security, policy, and reliability invariants of the control plane.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from backend.models.proposals import ActionProposal, ApprovalRecord
from backend.cortex.gateway import CortexExecutionGateway
from backend.cortex.guard import CortexGuard
from backend.cortex.ledger import ledger
from backend.execution.tool_registry import tool_registry
from backend.execution.idempotency import idempotency_manager
from backend.execution.locks import resource_lock_manager
from backend.execution.anti_thrashing import anti_thrashing_manager
from backend.execution.retry import incident_budget
from backend.observability.metrics_collector import metrics_collector
from backend.observability.telemetry_models import ServiceTelemetry, ObservabilityStatus
from backend.chaos.engine import chaos_engine
from backend.verification.verifier import verifier
from backend.providers.base import CloudProvider


class MockTestProvider(CloudProvider):
    """Predictable mock provider for testing gateway invariants."""
    def __init__(self):
        self.scale_called = False
        self.restart_called = False
        self.rollback_called = False

    def list_resources(self):
        return []

    def get_resource_state(self, resource_id):
        return {"id": resource_id, "status": "UP"}

    def get_metrics(self, resource_id):
        return {"p95_ms": 100.0, "error_rate": 0.001}

    def restart_service(self, service_name):
        self.restart_called = True
        return {"status": "SUCCESS", "action": "restart"}

    def scale_service(self, service_name, replicas):
        self.scale_called = True
        return {"status": "SUCCESS", "replicas": replicas}

    def rollback_service(self, service_name, revision=None):
        self.rollback_called = True
        return {"status": "SUCCESS", "action": "rollback"}

    def health_check(self, service_name):
        return {"healthy": True}

    def estimate_cost(self, action_type, params):
        return 0.0


@pytest.fixture(autouse=True)
def reset_safety_state():
    anti_thrashing_manager._last_mutations.clear()
    resource_lock_manager._active_holders.clear()
    yield
    anti_thrashing_manager._last_mutations.clear()
    resource_lock_manager._active_holders.clear()


# -----------------------------------------------------------------------------
# INVARIANT 1: AI Agent / LLM can NEVER execute infrastructure directly
# -----------------------------------------------------------------------------
def test_invariant_1_llm_cannot_execute_directly():
    from backend.orchestrator.agent import IncidentAgent
    agent = IncidentAgent()
    record = agent.handle_incident({
        "id": "INC-TEST-INV1",
        "service": "payment-service",
        "title": "Latency surge",
        "description": "High latency on payment-service"
    })
    # Action result must be PROPOSED, never EXECUTED directly by the agent
    act = record["action"]
    res = act.get("result", {})
    status = res.get("status") if isinstance(res, dict) else res
    assert status == "PROPOSED"


# -----------------------------------------------------------------------------
# INVARIANT 2: BLOCKED action can NEVER reach provider
# -----------------------------------------------------------------------------
def test_invariant_2_blocked_action_never_reaches_provider():
    mock_provider = MockTestProvider()
    guard = CortexGuard()
    gateway = CortexExecutionGateway(guard=guard, provider=mock_provider)

    # Database restart is blocked by POL-001
    proposal = ActionProposal(
        incident_id="INC-INV2",
        action_type="restart_database",
        target="postgres",
        params={"database": "postgres"},
        risk_score=95,
        reason="Test blocked DB restart",
        generated_by="test-agent"
    )

    result = gateway.evaluate_and_execute(proposal)
    assert result.status == "BLOCKED"
    assert mock_provider.restart_called is False
    assert mock_provider.scale_called is False


# -----------------------------------------------------------------------------
# INVARIANT 3: Unapproved action requiring authorization cannot execute
# -----------------------------------------------------------------------------
def test_invariant_3_unapproved_action_cannot_execute():
    mock_provider = MockTestProvider()
    guard = CortexGuard()
    guard.set_autonomy_level(1)  # Level 1 mandates human approval for mutations
    gateway = CortexExecutionGateway(guard=guard, provider=mock_provider)

    proposal = ActionProposal(
        incident_id="INC-INV3",
        action_type="scale_service",
        target="payment-service",
        params={"service": "payment-service", "replicas": 4},
        risk_score=75,
        reason="Test high risk downscale",
        generated_by="test-agent"
    )

    result = gateway.evaluate_and_execute(proposal)
    assert result.status == "BLOCKED"
    assert "approval_id" in result.output
    assert mock_provider.scale_called is False


# -----------------------------------------------------------------------------
# INVARIANT 4: Expired authorization token cannot execute
# -----------------------------------------------------------------------------
def test_invariant_4_expired_approval_fails():
    mock_provider = MockTestProvider()
    guard = CortexGuard()
    guard.set_autonomy_level(1)
    gateway = CortexExecutionGateway(guard=guard, provider=mock_provider)

    # Create expired token
    expired_token = ApprovalRecord(
        approval_id="app_expired_123",
        proposal_id="prop_expired",
        incident_id="INC-INV4",
        action_type="scale_service",
        target="payment-service",
        params={"replicas": 4},
        risk_score=80,
        reason="Needs approval",
        status="APPROVED",
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=60)
    )
    gateway.approved_tokens["app_expired_123"] = expired_token

    proposal = ActionProposal(
        proposal_id="prop_expired",
        incident_id="INC-INV4",
        action_type="scale_service",
        target="payment-service",
        params={"replicas": 4},
        risk_score=80,
        reason="Needs approval",
        generated_by="test-agent"
    )

    result = gateway.evaluate_and_execute(proposal, approval_id="app_expired_123")
    assert result.status == "BLOCKED"
    assert "EXPIRED" in result.output.get("error", "")
    assert mock_provider.scale_called is False


# -----------------------------------------------------------------------------
# INVARIANT 5: System freeze / kill switch immediately blocks mutations
# -----------------------------------------------------------------------------
def test_invariant_5_mutation_freeze_blocks_all_mutations():
    mock_provider = MockTestProvider()
    gateway = CortexExecutionGateway(provider=mock_provider)
    gateway.set_freeze_mutations(True)

    proposal = ActionProposal(
        incident_id="INC-INV5",
        action_type="scale_service",
        target="payment-service",
        params={"replicas": 4},
        risk_score=20,
        reason="Benign scale",
        generated_by="test-agent"
    )

    result = gateway.evaluate_and_execute(proposal)
    assert result.status == "BLOCKED"
    assert result.output.get("freeze_active") is True
    assert mock_provider.scale_called is False

    # Restore un-frozen state
    gateway.set_freeze_mutations(False)


# -----------------------------------------------------------------------------
# INVARIANT 6: Idempotency check prevents duplicate execution
# -----------------------------------------------------------------------------
def test_invariant_6_idempotency_prevents_duplicate_execution():
    mock_provider = MockTestProvider()
    gateway = CortexExecutionGateway(provider=mock_provider)

    key = f"test_idemp_key_{int(time.time()*1000)}"
    proposal = ActionProposal(
        incident_id="INC-INV6",
        action_type="restart_service",
        target="inventory-service",
        params={"service": "inventory-service"},
        risk_score=30,
        reason="Restart service",
        generated_by="test-agent"
    )

    # First execution succeeds
    res1 = gateway.evaluate_and_execute(proposal, idempotency_key=key)
    assert res1.status == "SUCCESS"
    assert mock_provider.restart_called is True

    # Reset mock tracker
    mock_provider.restart_called = False

    # Second execution with same idempotency key returns cached output without provider call
    res2 = gateway.evaluate_and_execute(proposal, idempotency_key=key)
    assert res2.status == "SUCCESS"
    assert mock_provider.restart_called is False  # Provider was NOT called again!


# -----------------------------------------------------------------------------
# INVARIANT 7: Resource lock prevents concurrent overlapping mutations
# -----------------------------------------------------------------------------
def test_invariant_7_concurrent_resource_lock_prevents_conflict():
    mock_provider = MockTestProvider()
    gateway = CortexExecutionGateway(provider=mock_provider)

    service_target = "order-service"
    # Artificially lock resource
    resource_lock_manager.acquire(service_target, "other_op_999", timeout_sec=10.0)

    try:
        proposal = ActionProposal(
            incident_id="INC-INV7",
            action_type="restart_service",
            target=service_target,
            params={"service": service_target},
            risk_score=30,
            reason="Concurrent restart",
            generated_by="test-agent"
        )

        res = gateway.evaluate_and_execute(proposal)
        assert res.status == "BLOCKED"
        assert res.output.get("conflict") is True
        assert mock_provider.restart_called is False
    finally:
        resource_lock_manager.release(service_target, "other_op_999")


# -----------------------------------------------------------------------------
# INVARIANT 8: Anti-thrashing cooldown prevents rapid oscillation
# -----------------------------------------------------------------------------
def test_invariant_8_anti_thrashing_cooldown_blocks_rapid_mutation():
    mock_provider = MockTestProvider()
    gateway = CortexExecutionGateway(provider=mock_provider)

    service_target = "auth-service"
    # Artificially record immediate previous mutation
    anti_thrashing_manager.record_mutation(service_target, "restart_service")

    proposal = ActionProposal(
        incident_id="INC-INV8",
        action_type="restart_service",
        target=service_target,
        params={"service": service_target},
        risk_score=30,
        reason="Repeated restart during cooldown",
        generated_by="test-agent"
    )

    res = gateway.evaluate_and_execute(proposal)
    assert res.status == "BLOCKED"
    assert "cooldown_remaining_sec" in res.output
    assert mock_provider.restart_called is False


# -----------------------------------------------------------------------------
# INVARIANT 9: Incident action budget prevents runaway attempts (max 3)
# -----------------------------------------------------------------------------
def test_invariant_9_incident_budget_blocks_after_3_attempts():
    mock_provider = MockTestProvider()
    gateway = CortexExecutionGateway(provider=mock_provider)

    inc_id = f"INC-BUDGET-{int(time.time()*1000)}"
    # Record 3 prior attempts
    incident_budget.increment(inc_id)
    incident_budget.increment(inc_id)
    incident_budget.increment(inc_id)

    proposal = ActionProposal(
        incident_id=inc_id,
        action_type="scale_service",
        target="payment-service",
        params={"replicas": 8},
        risk_score=40,
        reason="4th autonomous attempt",
        generated_by="test-agent"
    )

    res = gateway.evaluate_and_execute(proposal)
    assert res.status == "BLOCKED"
    assert res.output.get("escalated") is True


# -----------------------------------------------------------------------------
# INVARIANT 10: Stale telemetry (>60s) strictly blocks high-risk actions
# -----------------------------------------------------------------------------
def test_invariant_10_stale_telemetry_blocks_high_risk_actions():
    mock_provider = MockTestProvider()
    gateway = CortexExecutionGateway(provider=mock_provider)

    # Mock metrics_collector to return STALE telemetry (>60s old)
    stale_telemetry = ServiceTelemetry(
        service="payment-service",
        p95_latency_ms=120.0,
        error_rate_pct=0.01,
        cpu_percent=45.0,
        memory_percent=50.0,
        active_replicas=4,
        timestamp=time.time() - 90.0  # 90 seconds old!
    )

    with patch.object(metrics_collector, "collect", return_value=stale_telemetry):
        proposal = ActionProposal(
            incident_id="INC-INV10",
            action_type="scale_service",
            target="payment-service",
            params={"replicas": 8},
            risk_score=60,
            reason="Scale on stale telemetry",
            generated_by="test-agent"
        )

        res = gateway.evaluate_and_execute(proposal)
        assert res.status == "BLOCKED"
        assert res.output.get("telemetry_freshness") == "STALE"
        assert mock_provider.scale_called is False


# -----------------------------------------------------------------------------
# INVARIANT 11: Degrading outcome ('WORSE') triggers real automated rollback
# -----------------------------------------------------------------------------
def test_invariant_11_degraded_outcome_triggers_automatic_rollback():
    res = verifier.verify_action(
        operation_id="op_regression_test",
        target_service="payment-service",
        action_type="scale_down",
        pre_metrics={"error_rate": 0.005, "p95_ms": 110.0},
        post_metrics={"error_rate": 0.060, "p95_ms": 420.0}
    )

    assert res.outcome == "WORSE"
    assert res.rollback_triggered is True
    assert res.rollback_result is not None
    assert res.rollback_result["action"] == "automated_rollback"


# -----------------------------------------------------------------------------
# INVARIANT 12: Degraded observability reduces autonomy level
# -----------------------------------------------------------------------------
def test_invariant_12_degraded_observability_reduces_autonomy():
    mock_provider = MockTestProvider()
    gateway = CortexExecutionGateway(provider=mock_provider)

    normal_telemetry = ServiceTelemetry(
        service="payment-service",
        p95_latency_ms=100.0,
        error_rate_pct=0.01,
        cpu_percent=30.0,
        memory_percent=40.0,
        active_replicas=4,
        timestamp=time.time()
    )
    degraded_status = ObservabilityStatus(
        primary_collector_healthy=False,
        secondary_probe_healthy=True,
        overall_status="OBSERVABILITY_DEGRADED",
        autonomy_cap_level=1
    )

    with patch.object(metrics_collector, "collect", return_value=normal_telemetry):
        with patch.object(metrics_collector, "get_status", return_value=degraded_status):
            proposal = ActionProposal(
                incident_id="INC-INV12",
                action_type="scale_service",
                target="payment-service",
                params={"replicas": 8},
                risk_score=60,
                reason="Scale during degraded observability",
                generated_by="test-agent"
            )

            res = gateway.evaluate_and_execute(proposal)
            assert res.status == "BLOCKED"
            assert res.output.get("approval_required") is True


# -----------------------------------------------------------------------------
# INVARIANT 13: Chaos strictly blocked in non-sandbox environment
# -----------------------------------------------------------------------------
def test_invariant_13_chaos_strictly_blocked_in_non_sandbox():
    with pytest.raises(PermissionError) as exc_info:
        chaos_engine.inject_fault(
            target_service="payment-service",
            fault_type="crash",
            environment="production"
        )
    assert "SAFETY INVARIANT VIOLATION" in str(exc_info.value)


# -----------------------------------------------------------------------------
# INVARIANT 14: Unknown tool rejected by ToolRegistry
# -----------------------------------------------------------------------------
def test_invariant_14_unknown_tool_rejected_by_registry():
    mock_provider = MockTestProvider()
    gateway = CortexExecutionGateway(provider=mock_provider)

    proposal = ActionProposal(
        incident_id="INC-INV14",
        action_type="rm_rf_root_server",
        target="payment-service",
        params={},
        risk_score=99,
        reason="Malicious or un-registered tool",
        generated_by="rogue-agent"
    )

    res = gateway.evaluate_and_execute(proposal)
    assert res.status == "BLOCKED"
    assert "not registered in ToolRegistry" in res.output.get("error", "")


# -----------------------------------------------------------------------------
# INVARIANT 15: Tamper-evident ledger detects hash chain modifications
# -----------------------------------------------------------------------------
def test_invariant_15_tamper_evident_ledger_detects_hash_tampering():
    import json
    # Verify current clean integrity
    initial_check = ledger.verify_integrity()
    assert initial_check["valid"] is True

    # Artificially record an event
    ledger.record_event("test_audit_event", "test_actor", {"test": True})
    assert ledger.verify_integrity()["valid"] is True

    # Tamper with the ledger file on disk: alter the payload of the last record without updating hash
    with open(ledger.path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    original_last_line = lines[-1]
    last_rec = json.loads(original_last_line)
    last_rec["payload"] = {"malicious_tamper": True}
    lines[-1] = json.dumps(last_rec)

    with open(ledger.path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    tamper_check = ledger.verify_integrity()
    assert tamper_check["valid"] is False
    assert "Content tampering detected" in tamper_check["reason"]

    # Restore legitimate file
    lines[-1] = original_last_line
    with open(ledger.path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    restored_check = ledger.verify_integrity()
    assert restored_check["valid"] is True
