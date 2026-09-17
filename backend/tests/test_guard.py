"""
CORTEX Cloud Autopilot — CORTEX Guard & Governance Tests
"""

import pytest
from backend.cortex.guard import CortexGuard, guard
from backend.cortex.policies import ACTIVE_POLICIES


def test_guard_initial_state():
    g = CortexGuard()
    assert g.autonomy_level == 2
    assert g.kill_switch_engaged is False
    assert len(ACTIVE_POLICIES) >= 4


def test_kill_switch_blocks_evaluation():
    g = CortexGuard()
    g.set_kill_switch(True, reason="Emergency drill")
    assert g.kill_switch_engaged is True

    res = g.evaluate_action(
        action_type="scale_service",
        params={"service": "payment-service", "replicas": 4},
        incident_id="INC-TEST"
    )
    assert res["decision"] == "BLOCK"
    assert "KILL SWITCH ENGAGED" in res["reasons"][0]


def test_autonomy_level_0_blocks_all():
    g = CortexGuard()
    g.set_autonomy_level(0)
    res = g.evaluate_action(
        action_type="scale_service",
        params={"service": "payment-service", "replicas": 4},
        incident_id="INC-TEST"
    )
    assert res["decision"] == "BLOCK"
    assert "Autonomy Level 0" in res["reasons"][0]


def test_autonomy_level_1_requires_approval():
    g = CortexGuard()
    g.set_autonomy_level(1)
    res = g.evaluate_action(
        action_type="scale_service",
        params={"service": "payment-service", "replicas": 4},
        incident_id="INC-TEST"
    )
    assert res["decision"] == "REQUIRE_APPROVAL"
    assert "approval_id" in res


def test_policy_pol_001_database_restart_blocked():
    g = CortexGuard()
    res = g.evaluate_action(
        action_type="restart_database",
        params={"database": "postgres"},
        incident_id="INC-DB-TEST"
    )
    assert res["decision"] == "BLOCK"
    assert any("POL-001" in r for r in res["reasons"])
