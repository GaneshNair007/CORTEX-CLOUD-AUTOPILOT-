"""
CORTEX Cloud Autopilot — Execution Gateway Unit Tests
"""

import pytest
from backend.models.proposals import ActionProposal
from backend.cortex.gateway import execution_gateway, CortexExecutionGateway
from backend.execution.tool_registry import tool_registry
from backend.execution.idempotency import idempotency_manager


def test_tool_registry_validation():
    # Known tool passes validation
    assert tool_registry.is_registered("scale_service") is True
    tool = tool_registry.get("scale_service")
    assert tool is not None
    assert tool.mutating is True

    # Unknown tool fails validation
    assert tool_registry.is_registered("format_c_drive") is False


def test_gateway_dry_run():
    proposal = ActionProposal(
        incident_id="INC-DRY-RUN",
        action_type="scale_service",
        target="payment-service",
        params={"replicas": 4},
        risk_score=20,
        reason="Test benign scaling",
        generated_by="test-suite"
    )

    # In dry run, action passes guard check without mutating
    res = execution_gateway.evaluate_and_execute(proposal)
    assert res.status in ("SUCCESS", "BLOCKED")
    assert res.operation_id.startswith("op_")
