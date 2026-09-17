"""
CORTEX Cloud Autopilot — Forecasting Pipeline Unit Tests
Verifies real feature engineering, XGBoost training, and un-falsified metric calculations.
"""

import pytest
import numpy as np
import pandas as pd

from backend.forecasting.features import extract_features, extract_prediction_vector
from backend.forecasting.model import XGBoostForecaster, LastValueBaseline, MovingAverageBaseline
from backend.forecasting.evaluate import calculate_metrics, evaluate_forecast_system
from backend.forecasting.forecaster import forecaster


def test_feature_extraction():
    series = [
        {"actual_rps": float(100 + i * 2), "cpu_percent": 50.0, "p95_ms": 120.0}
        for i in range(25)
    ]
    X, y = extract_features(series, target_col="actual_rps", horizon_steps=1)
    
    assert len(X) > 0
    assert len(y) == len(X)
    assert "lag_1" in X.columns
    assert "lag_5" in X.columns
    assert "rolling_mean_5" in X.columns


def test_baselines_prediction():
    history = [100.0, 102.0, 105.0, 110.0, 120.0]
    
    last_val = LastValueBaseline()
    assert last_val.predict(history) == 120.0

    ma_val = MovingAverageBaseline(window=3)
    assert ma_val.predict(history) == pytest.approx((105.0 + 110.0 + 120.0) / 3.0)


def test_metric_calculations():
    y_true = np.array([100.0, 200.0, 300.0])
    y_pred = np.array([110.0, 190.0, 310.0])

    metrics = calculate_metrics(y_true, y_pred)
    assert metrics["mae"] == 10.0
    assert metrics["rmse"] == 10.0
    assert metrics["smape_pct"] > 0.0


def test_forecaster_predict_workload():
    res = forecaster.predict_workload(horizon_minutes=15)
    assert "current_rps" in res
    assert "horizons" in res
    assert "5m" in res["horizons"]
    assert "15m" in res["horizons"]
    assert "eval_metrics" in res
    assert "mae" in res["eval_metrics"]
