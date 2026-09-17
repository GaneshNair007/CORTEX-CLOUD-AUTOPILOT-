"""
CORTEX Cloud Autopilot — Multi-Objective Optimizer Tests
"""

import pytest
from backend.optimization.optimizer import optimizer


def test_optimizer_balanced_mode():
    res = optimizer.optimize(mode="BALANCED", current_replicas=4, forecast_rps=400.0)
    assert "recommended_replicas" in res
    assert "mode" in res
    assert res["mode"] == "BALANCED"
    assert res["recommended_replicas"] >= 2  # Hard minimum constraint
    assert "trade_offs" in res
    assert "latency_ms" in res["trade_offs"]
    assert "hourly_cost_usd" in res["trade_offs"]


def test_optimizer_modes():
    modes = ["COST", "PERFORMANCE", "RELIABILITY", "GREEN", "EMERGENCY"]
    for m in modes:
        res = optimizer.optimize(mode=m, current_replicas=6, forecast_rps=450.0)
        assert res["mode"] == m
        assert res["recommended_replicas"] >= 2


def test_optimizer_hard_constraint_minimum_replicas():
    # Even if RPS is 0, optimizer must never scale below 2 replicas
    res = optimizer.optimize(mode="COST", current_replicas=4, forecast_rps=1.0)
    assert res["recommended_replicas"] >= 2
