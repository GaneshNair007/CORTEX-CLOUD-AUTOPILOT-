try:
    from backend.forecasting.forecaster import forecaster, WorkloadForecaster
    from backend.forecasting.anomalies import anomaly_detector, AnomalyDetector
except ImportError:
    from forecasting.forecaster import forecaster, WorkloadForecaster
    from forecasting.anomalies import anomaly_detector, AnomalyDetector

__all__ = ["forecaster", "WorkloadForecaster", "anomaly_detector", "AnomalyDetector"]
