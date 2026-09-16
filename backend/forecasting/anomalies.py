"""
CORTEX Cloud Autopilot — Telemetry Anomaly Detector
Uses Isolation Forest to detect multivariate anomalies across CPU, RAM, RPS, and latency.
"""

from typing import Dict, Any, List
import numpy as np
from sklearn.ensemble import IsolationForest


class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.05, random_state=42)
        self._fit_baseline_distribution()

    def _fit_baseline_distribution(self) -> None:
        """Trains an initial normal distribution model representing healthy traffic."""
        # Synthesize 300 normal telemetry vectors: [CPU, RAM, RPS, P95_ms, Error_Rate]
        np.random.seed(42)
        n_samples = 300
        normal_cpu = np.random.normal(loc=45.0, scale=8.0, size=n_samples)
        normal_ram = np.random.normal(loc=55.0, scale=6.0, size=n_samples)
        normal_rps = np.random.normal(loc=350.0, scale=40.0, size=n_samples)
        normal_p95 = np.random.normal(loc=120.0, scale=15.0, size=n_samples)
        normal_err = np.random.exponential(scale=0.002, size=n_samples)

        X_train = np.column_stack([normal_cpu, normal_ram, normal_rps, normal_p95, normal_err])
        self.model.fit(X_train)

    def detect_anomaly(self, cpu: float, ram: float, rps: float, p95_ms: float, error_rate: float) -> Dict[str, Any]:
        """Evaluates live telemetry vector and scores anomaly likelihood."""
        vector = np.array([[cpu, ram, rps, p95_ms, error_rate]])
        prediction = self.model.predict(vector)[0]  # 1 = Normal, -1 = Anomaly
        raw_score = self.model.decision_function(vector)[0]

        # Normalize score: lower decision function means more anomalous
        # Normalize into 0 to 100 anomaly confidence score
        anomaly_score = round(max(0.0, min(100.0, (0.2 - raw_score) * 250.0)), 1)
        is_anomalous = prediction == -1 or anomaly_score > 65.0

        anomalous_features = []
        if cpu > 80.0:
            anomalous_features.append(f"CPU high ({cpu:.1f}%)")
        if p95_ms > 200.0:
            anomalous_features.append(f"p95 latency spike ({p95_ms:.1f}ms)")
        if error_rate > 0.02:
            anomalous_features.append(f"Error rate elevated ({error_rate * 100:.2f}%)")
        if rps > 500.0:
            anomalous_features.append(f"Unusual traffic volume ({rps:.1f} RPS)")

        return {
            "is_anomaly": is_anomalous,
            "anomaly_score": anomaly_score,
            "decision": "ANOMALY_DETECTED" if is_anomalous else "NORMAL",
            "anomalous_features": anomalous_features,
            "telemetry_snapshot": {
                "cpu": cpu,
                "ram": ram,
                "rps": rps,
                "p95_ms": p95_ms,
                "error_rate": error_rate
            }
        }


# Global singleton anomaly detector
anomaly_detector = AnomalyDetector()
