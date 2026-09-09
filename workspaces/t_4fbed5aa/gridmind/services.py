"""GridMind service layer — orchestrates models and API."""

from __future__ import annotations

from typing import Any

from gridmind import LoadPredictor, FaultDetector, RenewableIntegrator
from gridmind.config import get_settings


class GridMindService:
    """Central service orchestrating all GridMind AI models."""

    def __init__(self):
        settings = get_settings()
        self.predictor = LoadPredictor()
        self.detector = FaultDetector()
        self.integrator = RenewableIntegrator()
        self.settings = settings

    def train_all(self, load_data: list[float], sensor_data: list[list[float]]) -> dict[str, Any]:
        """Train all models with provided data."""
        load_result = self.predictor.fit(load_data)
        sensor_arr = sensor_data if sensor_data else [[0.0] * self.detector.sensor_dims]
        sensor_flat = [v for row in sensor_arr for v in row]
        self.detector.sensor_dims = len(sensor_flat)
        fault_result = self.detector.fit(np.array(sensor_arr[:100] if len(sensor_arr) >= 100 else sensor_arr), val_split=0.0)
        return {
            "load_training": load_result,
            "fault_training": fault_result,
            "all_trained": True,
        }

    def predict_load(self, recent_load: list[float], horizon_hours: int = 1) -> dict[str, Any]:
        return self.predictor.predict(recent_load, horizon_hours, confidence=True)

    def detect_faults(self, sensor_reading: list[float]) -> dict[str, Any]:
        self.detector.sensor_dims = len(sensor_reading)
        return self.detector.detect(sensor_reading, rules=True)

    def optimize_renewable_dispatch(
        self,
        load_forecast: list[float],
        renewable_forecast: list[float],
        current_storage: float = 0.0,
    ) -> dict[str, Any]:
        return self.integrator.optimize_dispatch(load_forecast, renewable_forecast, current_storage)


def create_service() -> GridMindService:
    return GridMindService()
