"""
CORTEX Cloud Autopilot — Master Control Plane Loop Tests
"""

import pytest
from backend.control_plane.pipeline import control_plane


def test_control_plane_run_loop():
    res = control_plane.run_control_loop(
        service="payment-service",
        severity="P1",
        symptom="High latency and 500 error spikes on /v1/checkout",
        simulate_dangerous=False
    )
    assert res["status"] == "success"
    assert "incident_id" in res
    assert "stages" in res
    stages = res["stages"]
    assert "observe" in stages
    assert "understand" in stages
    assert "predict" in stages
    assert "simulate" in stages
    assert "optimize" in stages
    assert "authorize" in stages
    assert "act" in stages
    assert "events" in res


def test_control_plane_blocks_dangerous_database_restart():
    res = control_plane.run_control_loop(
        service="postgres",
        severity="P0",
        symptom="Database connection saturation",
        simulate_dangerous=True
    )
    assert res["status"] == "success"
    # Action result must be BLOCKED
    act_res = res["action_result"]
    assert act_res["status"] == "BLOCKED"
    assert res["stages"]["authorize"]["decision"] == "BLOCK"
