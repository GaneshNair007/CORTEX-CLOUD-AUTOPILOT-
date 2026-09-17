"""
CORTEX Cloud Autopilot — Closed-Loop Verification & SLO Tests
Verifies mathematical SLO target evaluations and rollback dispatching.
"""

import pytest
from backend.slo.config import get_slo_for_service, calculate_burn_rate, calculate_error_budget_remaining
from backend.verification.verifier import verifier


def test_slo_lookup():
    payment_slo = get_slo_for_service("payment-service")
    assert payment_slo.service == "payment-service"
    assert payment_slo.max_error_rate == 0.010
    assert payment_slo.max_p95_ms == 200.0


def test_error_budget_calculation():
    slo = get_slo_for_service("payment-service")
    res = calculate_error_budget_remaining(total_requests=10000, error_count=50, slo=slo)
    assert res["status"] == "HEALTHY"
    assert res["budget_remaining_pct"] == 50.0  # Allowed 100, used 50 -> 50% remaining


def test_burn_rate_calculation():
    slo = get_slo_for_service("payment-service")
    # 0.02 error rate when SLO is 0.01 = 2.0x burn rate
    burn = calculate_burn_rate(observed_error_rate=0.02, slo=slo)
    assert burn == 2.0


def test_verification_recovered():
    res = verifier.verify_action(
        operation_id="op_rec_test",
        target_service="payment-service",
        action_type="scale_service",
        pre_metrics={"error_rate": 0.04, "p95_ms": 350.0},
        post_metrics={"error_rate": 0.003, "p95_ms": 120.0}
    )
    assert res.outcome == "RECOVERED"
    assert res.slo_satisfied is True
    assert res.rollback_triggered is False


def test_verification_partially_recovered():
    res = verifier.verify_action(
        operation_id="op_part_test",
        target_service="payment-service",
        action_type="scale_service",
        pre_metrics={"error_rate": 0.08, "p95_ms": 500.0},
        post_metrics={"error_rate": 0.03, "p95_ms": 220.0}  # Better, but still above 0.01 and 200ms
    )
    assert res.outcome == "PARTIALLY_RECOVERED"
    assert res.slo_satisfied is False
    assert res.rollback_triggered is False
