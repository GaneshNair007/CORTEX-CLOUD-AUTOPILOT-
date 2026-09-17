"""
CORTEX Cloud Autopilot — Forecast Model Evaluation
Computes true mathematical evaluation metrics (MAE, RMSE, sMAPE) on held-out test sets.
Strictly avoids fabricated/hardcoded metrics.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Computes true regression metrics:
      - MAE: Mean Absolute Error
      - RMSE: Root Mean Squared Error
      - SMAPE: Symmetric Mean Absolute Percentage Error (%)
      - MAPE: Mean Absolute Percentage Error (%)
    """
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    if len(y_true) == 0 or len(y_pred) == 0:
        return {"mae": 0.0, "rmse": 0.0, "smape_pct": 0.0, "mape_pct": 0.0}

    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    # Avoid division by zero in percentage errors
    denominator = np.abs(y_true) + np.abs(y_pred)
    zero_mask = denominator == 0
    smape_elements = np.zeros_like(y_true)
    smape_elements[~zero_mask] = 200.0 * np.abs(y_pred[~zero_mask] - y_true[~zero_mask]) / denominator[~zero_mask]
    smape = float(np.mean(smape_elements))

    safe_y_true = np.where(y_true == 0, 1e-5, y_true)
    mape = float(np.mean(np.abs((y_true - y_pred) / safe_y_true)) * 100.0)

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "smape_pct": round(smape, 2),
        "mape_pct": round(mape, 2),
    }


def evaluate_forecast_system(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    recent_history: List[float]
) -> Dict[str, Any]:
    """
    Evaluates trained model against Last-Value and Moving-Average baselines.
    """
    point_preds, _, _ = model.predict(X_test)
    model_metrics = calculate_metrics(y_test.to_numpy(), point_preds)

    # Last value baseline
    last_val = recent_history[-1] if recent_history else float(y_test.iloc[0])
    last_val_preds = np.full_like(y_test.to_numpy(), last_val)
    last_val_metrics = calculate_metrics(y_test.to_numpy(), last_val_preds)

    # Moving average baseline
    ma_val = float(np.mean(recent_history[-5:])) if recent_history else float(y_test.iloc[0])
    ma_preds = np.full_like(y_test.to_numpy(), ma_val)
    ma_metrics = calculate_metrics(y_test.to_numpy(), ma_preds)

    return {
        "model_type": model.model_type,
        "sample_count": len(y_test),
        "model_metrics": model_metrics,
        "baselines": {
            "last_value": last_val_metrics,
            "moving_average_5": ma_metrics
        },
        "outperforms_naive_baseline": model_metrics["mae"] <= last_val_metrics["mae"]
    }
