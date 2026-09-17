"""
CORTEX Cloud Autopilot — Workload Forecaster Training Pipeline
Trains model on time-series telemetry, evaluates on held-out split, and saves artifact.
"""

import os
import math
import time
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

from backend.forecasting.features import extract_features
from backend.forecasting.model import XGBoostForecaster
from backend.forecasting.evaluate import evaluate_forecast_system

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "workload_model.pkl"
METADATA_PATH = ARTIFACTS_DIR / "model_metadata.json"


def generate_synthetic_telemetry(points: int = 1440, base_rps: float = 350.0) -> List[Dict[str, Any]]:
    """Generates realistic cyclical diurnal workload data with realistic micro-bursts."""
    data = []
    np.random.seed(42)
    now = time.time() - (points * 60)

    for i in range(points):
        t = now + (i * 60)
        minute_of_day = (i % 1440)
        
        # Diurnal pattern (peak at 14:00, trough at 04:00)
        diurnal = math.sin((minute_of_day - 240) / 1440.0 * 2 * math.pi) * 120.0
        
        # Periodic lunch-time surge
        surge = 60.0 if 720 <= minute_of_day <= 840 else 0.0
        
        # Random walk noise
        noise = np.random.normal(0, 12.0)
        
        rps = max(30.0, base_rps + diurnal + surge + noise)
        cpu = min(98.0, max(5.0, (rps / 5.5) + np.random.normal(0, 3.0)))
        p95 = max(20.0, 60.0 + (rps / 4.0) + np.random.normal(0, 4.0))

        data.append({
            "timestamp": t,
            "actual_rps": round(rps, 2),
            "cpu_percent": round(cpu, 2),
            "p95_ms": round(p95, 2)
        })

    return data


def train_forecasting_model(data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Trains the XGBoostForecaster on telemetry, evaluates on held-out split,
    and persists the artifact.
    """
    if data is None:
        data = generate_synthetic_telemetry(points=1440)

    # 1. Feature extraction
    X, y = extract_features(data, target_col="actual_rps", horizon_steps=1)

    # 2. Time-based train-test split (80% train, 20% test)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # 3. Train model
    forecaster = XGBoostForecaster(n_estimators=80, max_depth=4, learning_rate=0.08)
    forecaster.fit(X_train, y_train)

    # 4. Evaluate against real test data
    recent_history = [d["actual_rps"] for d in data[:split_idx]]
    eval_result = evaluate_forecast_system(forecaster, X_test, y_test, recent_history)

    # 5. Persist artifact
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    forecaster.save(str(MODEL_PATH))

    # Save metadata
    import json
    metadata = {
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_type": forecaster.model_type,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "metrics": eval_result["model_metrics"],
        "baselines": eval_result["baselines"],
        "residual_std": forecaster.residual_std,
        "feature_names": forecaster.feature_names
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    return metadata


if __name__ == "__main__":
    print("Training workload forecasting model...")
    meta = train_forecasting_model()
    print("Training complete! Metadata:")
    print(meta)
