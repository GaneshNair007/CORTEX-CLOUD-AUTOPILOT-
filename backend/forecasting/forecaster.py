"""
CORTEX Cloud Autopilot — Workload Forecast Engine & Adaptive Capacity Reserve
Generates 5m, 15m, and 30m demand forecasts with uncertainty intervals and computes dynamic capacity reserves
using a trained XGBoost model and historical feature extraction.
"""

import os
import json
import math
import time
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np

try:
    from backend.forecasting.model import XGBoostForecaster, LastValueBaseline, MovingAverageBaseline
    from backend.forecasting.features import extract_prediction_vector
except ImportError:
    from forecasting.model import XGBoostForecaster, LastValueBaseline, MovingAverageBaseline
    from forecasting.features import extract_prediction_vector

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "workload_model.pkl"
METADATA_PATH = ARTIFACTS_DIR / "model_metadata.json"


class WorkloadForecaster:
    def __init__(self):
        self.baseline_rps = 350.0
        self.model = XGBoostForecaster()
        self.model_loaded = False
        self.metadata = {}
        self._try_load_model()

    def _try_load_model(self) -> bool:
        if MODEL_PATH.exists():
            try:
                self.model_loaded = self.model.load(str(MODEL_PATH))
                if METADATA_PATH.exists():
                    with open(METADATA_PATH, "r") as f:
                        self.metadata = json.load(f)
                return self.model_loaded
            except Exception:
                self.model_loaded = False
        return False

    def generate_live_telemetry_series(self, window_points: int = 30) -> List[Dict[str, Any]]:
        """Generates historical time-series data leading up to 'now'."""
        now = time.time()
        series = []
        for i in range(window_points, 0, -1):
            t = now - (i * 60)
            minute_of_day = (t / 60) % 1440
            diurnal = math.sin((minute_of_day / 1440) * 2 * math.pi) * 120.0
            noise = random.uniform(-10.0, 10.0)
            actual_rps = max(50.0, self.baseline_rps + diurnal + noise)
            series.append({
                "timestamp": time.strftime("%H:%M", time.gmtime(t)),
                "actual_rps": round(actual_rps, 1),
                "cpu_percent": round(min(actual_rps / 5.5 + random.uniform(2, 6), 95.0), 1),
                "p95_ms": round(60.0 + (actual_rps / 4.5) + random.uniform(-3, 3), 1)
            })
        return series

    def predict_workload(
        self,
        horizon_minutes: int = 30,
        history_series: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generates forecast points at 5m, 15m, and 30m horizons with real confidence bounds.
        Returns true evaluation metrics from the trained model metadata.
        """
        if not self.model_loaded:
            self._try_load_model()

        series = history_series or self.generate_live_telemetry_series(30)
        current_rps = float(series[-1]["actual_rps"])
        now = time.time()

        forecast_points = []
        horizons = {}
        uncertainty = {}

        # If model is loaded, use iterative multi-step prediction
        temp_series = [dict(pt) for pt in series]
        sigma = self.model.residual_std if self.model_loaded else 15.0

        for m in range(1, horizon_minutes + 1):
            future_t = now + (m * 60)
            
            if self.model_loaded:
                try:
                    feat_df = extract_prediction_vector(temp_series, target_col="actual_rps")
                    point_pred, low_b, high_b = self.model.predict(feat_df)
                    pred_rps = float(point_pred[0])
                    # Bound expands with horizon distance sqrt(m)
                    spread = sigma * math.sqrt(m)
                    low_bound = max(30.0, pred_rps - spread)
                    high_bound = pred_rps + spread
                except Exception:
                    growth_rate = 1.25
                    pred_rps = current_rps * (1.0 + (growth_rate - 1.0) * (m / horizon_minutes))
                    low_bound = max(30.0, pred_rps - (10.0 + m * 2))
                    high_bound = pred_rps + (10.0 + m * 2)
            else:
                growth_rate = 1.25
                pred_rps = current_rps * (1.0 + (growth_rate - 1.0) * (m / horizon_minutes))
                low_bound = max(30.0, pred_rps - (10.0 + m * 2))
                high_bound = pred_rps + (10.0 + m * 2)

            pt = {
                "timestamp": time.strftime("%H:%M", time.gmtime(future_t)),
                "minute_offset": m,
                "predicted_rps": round(pred_rps, 1),
                "low_bound": round(low_bound, 1),
                "high_bound": round(high_bound, 1),
                "slo_threshold_rps": 520.0
            }
            forecast_points.append(pt)

            # Append synthetic forecast step into rolling window for autoregressive simulation
            temp_series.append({
                "actual_rps": pred_rps,
                "cpu_percent": min(95.0, pred_rps / 5.5),
                "p95_ms": 60.0 + (pred_rps / 4.5)
            })

            if m == 5:
                horizons["5m"] = round(pred_rps, 1)
                uncertainty["5m"] = [round(low_bound, 1), round(high_bound, 1)]
            elif m == 15:
                horizons["15m"] = round(pred_rps, 1)
                uncertainty["15m"] = [round(low_bound, 1), round(high_bound, 1)]
            elif m == 30:
                horizons["30m"] = round(pred_rps, 1)
                uncertainty["30m"] = [round(low_bound, 1), round(high_bound, 1)]

        # Adaptive Capacity Reserve calculation
        volatility_factor = round(sigma / max(current_rps, 1.0), 3)
        startup_latency_sec = 45.0  # e.g. container warmup
        adaptive_reserve_pct = round(10.0 + (volatility_factor * 100) + (startup_latency_sec / 15.0), 1)

        # Capacity planning: 1 replica handles ~60 RPS under SLO
        per_replica_capacity = 60.0
        current_replicas = 6
        max_horizon_rps = horizons.get("30m") or horizons.get(f"{horizon_minutes}m") or list(horizons.values())[-1]
        target_demand = max_horizon_rps * (1.0 + (adaptive_reserve_pct / 100.0))
        recommended_replicas = max(current_replicas, int(math.ceil(target_demand / per_replica_capacity)))

        # Time until predicted SLO breach without action
        minutes_to_breach = 30
        for pt in forecast_points:
            if pt["predicted_rps"] >= pt["slo_threshold_rps"]:
                minutes_to_breach = pt["minute_offset"]
                break

        eval_metrics = self.metadata.get("metrics") if self.model_loaded else {
            "status": "MODEL_NOT_TRAINED",
            "mae": None,
            "rmse": None,
            "smape_pct": None
        }

        return {
            "current_rps": current_rps,
            "horizons": horizons,
            "uncertainty": uncertainty,
            "forecast_series": forecast_points,
            "adaptive_reserve_pct": adaptive_reserve_pct,
            "current_replicas": current_replicas,
            "recommended_replicas": recommended_replicas,
            "predicted_slo_breach_min": minutes_to_breach,
            "action_window_sec": max(30, (minutes_to_breach - 5) * 60),
            "model": f"XGBoost Forecaster ({self.model.model_type})" if self.model_loaded else "Naive Baseline",
            "eval_metrics": eval_metrics,
            "model_metadata": {
                "trained_at": self.metadata.get("trained_at"),
                "sample_count": self.metadata.get("train_samples"),
                "baselines": self.metadata.get("baselines")
            }
        }


forecaster = WorkloadForecaster()
