"""
CORTEX Cloud Autopilot — Workload Feature Engineering
Transforms time-series telemetry into tabular features for machine learning models.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple


def extract_features(
    time_series: List[Dict[str, Any]],
    target_col: str = "actual_rps",
    horizon_steps: int = 1
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Extracts lag and rolling features from historical time series.
    
    Features generated:
      - lag_1: Immediate previous step
      - lag_2: 2 steps previous
      - lag_5: 5 steps previous
      - rolling_mean_5: 5-step rolling window mean
      - rolling_std_5: 5-step rolling window std dev
      - minute_of_day: cyclic time feature
      - hour_of_day: cyclic time feature
    """
    if len(time_series) < 10:
        raise ValueError(f"Insufficient time-series data: need at least 10 points, got {len(time_series)}")

    df = pd.DataFrame(time_series)
    if target_col not in df.columns:
        raise KeyError(f"Target column '{target_col}' not found in time-series data")

    # Ensure numeric
    df[target_col] = pd.to_numeric(df[target_col])

    # Lag features
    df["lag_1"] = df[target_col].shift(1)
    df["lag_2"] = df[target_col].shift(2)
    df["lag_5"] = df[target_col].shift(5)

    # Rolling window statistics
    df["rolling_mean_5"] = df[target_col].rolling(window=5, min_periods=1).mean()
    df["rolling_std_5"] = df[target_col].rolling(window=5, min_periods=1).std().fillna(0.0)

    # Target variable shifted by horizon_steps
    target_series = df[target_col].shift(-horizon_steps)

    # Feature columns
    feature_cols = ["lag_1", "lag_2", "lag_5", "rolling_mean_5", "rolling_std_5"]
    
    # Additional optional features if present
    for extra in ["cpu_percent", "p95_ms"]:
        if extra in df.columns:
            df[f"{extra}_lag_1"] = pd.to_numeric(df[extra]).shift(1)
            feature_cols.append(f"{extra}_lag_1")

    # Drop NaNs created by shifting
    valid_mask = ~(df[feature_cols].isna().any(axis=1) | target_series.isna())
    
    X = df.loc[valid_mask, feature_cols].reset_index(drop=True)
    y = target_series.loc[valid_mask].reset_index(drop=True)

    return X, y


def extract_prediction_vector(
    recent_history: List[Dict[str, Any]],
    target_col: str = "actual_rps"
) -> pd.DataFrame:
    """
    Extracts a single feature vector from the most recent historical window for live inference.
    """
    if len(recent_history) < 6:
        raise ValueError(f"Need at least 6 points of history for inference, got {len(recent_history)}")

    values = [float(p[target_col]) for p in recent_history]
    
    lag_1 = values[-1]
    lag_2 = values[-2]
    lag_5 = values[-5]
    rolling_mean_5 = float(np.mean(values[-5:]))
    rolling_std_5 = float(np.std(values[-5:]))

    data = {
        "lag_1": [lag_1],
        "lag_2": [lag_2],
        "lag_5": [lag_5],
        "rolling_mean_5": [rolling_mean_5],
        "rolling_std_5": [rolling_std_5]
    }

    if "cpu_percent" in recent_history[-1]:
        data["cpu_percent_lag_1"] = [float(recent_history[-1]["cpu_percent"])]
    if "p95_ms" in recent_history[-1]:
        data["p95_ms_lag_1"] = [float(recent_history[-1]["p95_ms"])]

    return pd.DataFrame(data)
