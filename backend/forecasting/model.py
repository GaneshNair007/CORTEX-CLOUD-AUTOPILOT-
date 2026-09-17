"""
CORTEX Cloud Autopilot — Workload Forecasting Models
Implements naive baselines and machine learning models for resource demand prediction.
"""

import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple


class LastValueBaseline:
    """Naive baseline: predicts the last observed value."""
    def predict(self, recent_values: list[float]) -> float:
        if not recent_values:
            return 0.0
        return float(recent_values[-1])


class MovingAverageBaseline:
    """Moving average baseline over window k."""
    def __init__(self, window: int = 5):
        self.window = window

    def predict(self, recent_values: list[float]) -> float:
        if not recent_values:
            return 0.0
        w = min(len(recent_values), self.window)
        return float(np.mean(recent_values[-w:]))


class XGBoostForecaster:
    """
    Gradient boosted decision trees for time-series demand forecasting.
    Includes fallback to GradientBoostingRegressor if xgboost C++ runtime is unavailable.
    """

    def __init__(self, n_estimators: int = 100, max_depth: int = 4, learning_rate: float = 0.08):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.model = None
        self.model_type = "none"
        self.residual_std = 10.0
        self.feature_names = []

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.feature_names = list(X.columns)
        try:
            import xgboost as xgb
            self.model = xgb.XGBRegressor(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                random_state=42,
                verbosity=0
            )
            self.model.fit(X, y)
            self.model_type = "xgboost"
        except Exception:
            from sklearn.ensemble import GradientBoostingRegressor
            self.model = GradientBoostingRegressor(
                n_estimators=self.n_estimators,
                max_depth=self.max_depth,
                learning_rate=self.learning_rate,
                random_state=42
            )
            self.model.fit(X, y)
            self.model_type = "sklearn_gbr"

        # Calculate residual standard deviation for uncertainty estimation
        preds = self.model.predict(X)
        residuals = y.to_numpy() - preds
        self.residual_std = max(5.0, float(np.std(residuals)))

    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generates predictions along with 95% confidence bounds (±1.96 * residual_std).
        """
        if self.model is None:
            raise RuntimeError("MODEL_NOT_TRAINED: Forecaster has not been fitted or loaded.")

        # Ensure correct column alignment
        X_aligned = X[self.feature_names] if self.feature_names else X
        point_preds = self.model.predict(X_aligned)
        
        low_bound = np.maximum(0.0, point_preds - (1.96 * self.residual_std))
        high_bound = point_preds + (1.96 * self.residual_std)

        return point_preds, low_bound, high_bound

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({
            "model": self.model,
            "model_type": self.model_type,
            "residual_std": self.residual_std,
            "feature_names": self.feature_names
        }, filepath)

    def load(self, filepath: str) -> bool:
        if not os.path.exists(filepath):
            return False
        data = joblib.load(filepath)
        self.model = data["model"]
        self.model_type = data.get("model_type", "xgboost")
        self.residual_std = data.get("residual_std", 10.0)
        self.feature_names = data.get("feature_names", [])
        return True
