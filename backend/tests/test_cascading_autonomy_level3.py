"""Tests for Level 3 Full Autonomy and Multi-Tier Cascading Failure Scenarios."""

import pytest
from backend.cortex.guard import CortexGuard
from backend.chaos.engine import ChaosEngine
from backend.models.proposals import ActionProposal


def test_autonomy_level_3_auto_executes_safe_scaling():
    """At Level 3 (Autopilot), safe scaling operations are auto-approved without human intervention."""
    guard = CortexGuard()
    guard.set_autonomy_level(3)

    decision = guard.evaluate_action(
        action_type="scale_deployment",
        params={"service": "payment-service", "replicas": 5},
        incident_id="INC-L3-01"
    )

    assert decision["decision"] == "ALLOW"
    assert decision["approval_id"] is None
    assert any("Autonomy Level 3" in r for r in decision["reasons"])


def test_autonomy_level_3_still_blocks_dangerous_database_restart():
    """At Level 3, security invariants and deterministic policies (POL-001) are NEVER bypassed."""
    guard = CortexGuard()
    guard.set_autonomy_level(3)

    decision = guard.evaluate_action(
        action_type="restart_database",
        params={"service": "postgres-primary"},
        incident_id="INC-L3-02"
    )

    # Must be BLOCKED by POL-001
    assert decision["decision"] == "BLOCK"
    assert any("POL-001" in r for r in decision["reasons"])


def test_autonomy_level_3_catastrophic_blast_radius_safeguard():
    """At Level 3, operations with catastrophic blast radius (>=90) still require human signoff."""
    guard = CortexGuard()
    guard.set_autonomy_level(3)

    # Mock high blast radius action
    decision = guard.evaluate_action(
        action_type="delete_resource",
        params={"service": "api-gateway"},
        incident_id="INC-L3-03"
    )

    assert decision["decision"] in ("BLOCK", "REQUIRE_APPROVAL")


def test_cascading_failure_lifecycle():
    """Verifies injection of multi-tier cascading outage across database -> payment -> gateway."""
    engine = ChaosEngine()
    cascade = engine.inject_cascading_failure(
        root_service="postgres",
        cascade_chain=["postgres", "payment-service", "api-gateway"],
        duration_sec=5,
        environment="sandbox"
    )

    assert cascade["status"] == "CASCADING_ACTIVE"
    assert cascade["tier_count"] == 3
    assert "postgres" in cascade["tier_results"]
    assert "payment-service" in cascade["tier_results"]
    assert "api-gateway" in cascade["tier_results"]

    # Cleanup
    for svc in cascade["cascade_chain"]:
        engine.clear_faults(svc, environment="sandbox")


def test_cascading_failure_safety_invariant():
    """Cascading failure injection strictly rejected outside sandbox environment."""
    engine = ChaosEngine()
    with pytest.raises(PermissionError) as exc_info:
        engine.inject_cascading_failure(
            root_service="postgres",
            environment="production"
        )
    assert "SAFETY INVARIANT" in str(exc_info.value)
