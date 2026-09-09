"""Tests for GridMind service layer and API integration."""

import pytest
from fastapi.testclient import TestClient

from gridmind import create_app
from gridmind.config import Settings


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def settings():
    return Settings(app_name="TestGrid", app_version="1.0.0")


class TestRootAndHealth:
    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert data["name"] == "GridMind AI Platform"

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "service" in data

    def test_health_full_endpoint(self, client):
        resp = client.get("/api/v1/health/full")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "services" in data


class TestLoadAPI:
    def test_train_load_model(self, client):
        resp = client.post("/api/v1/load/train", json={
            "load_values": [50.0, 52.0, 48.0, 51.0, 49.0, 53.0, 50.0, 48.0,
                           52.0, 51.0, 49.0, 50.0, 51.0, 48.0, 52.0, 50.0,
                           49.0, 51.0, 50.0, 48.0, 52.0, 51.0, 50.0, 49.0],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "final_train_loss" in data
        assert data["model_type"] == "lstm"

    def test_predict_load_untrained(self, client):
        resp = client.post("/api/v1/load/predict", json={
            "recent_load": [50.0] * 24,
            "horizon_hours": 1,
        })
        assert resp.status_code == 409

    def test_predict_load_after_training(self, client):
        client.post("/api/v1/load/train", json={
            "load_values": [50.0, 52.0, 48.0, 51.0, 49.0, 53.0, 50.0, 48.0,
                           52.0, 51.0, 49.0, 50.0, 51.0, 48.0, 52.0, 50.0,
                           49.0, 51.0, 50.0, 48.0, 52.0, 51.0, 50.0, 49.0],
        })
        resp = client.post("/api/v1/load/predict", json={
            "recent_load": [50.0] * 24,
            "horizon_hours": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "predicted_load" in data
        assert data["predicted_load"] >= 0

    def test_load_status(self, client):
        resp = client.get("/api/v1/load/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_type"] == "lstm"
        assert data["trained"] is False

    def test_load_evaluate(self, client):
        resp = client.get("/api/v1/load/evaluate?actual=50.0,52.0,48.0&predicted=51.0,50.0,49.0")
        assert resp.status_code == 200
        data = resp.json()
        assert "mae" in data

    def test_batch_predict_after_training(self, client):
        client.post("/api/v1/load/train", json={
            "load_values": [50.0, 52.0, 48.0, 51.0, 49.0, 53.0, 50.0, 48.0,
                           52.0, 51.0, 49.0, 50.0, 51.0, 48.0, 52.0, 50.0,
                           49.0, 51.0, 50.0, 48.0, 52.0, 51.0, 50.0, 49.0],
        })
        resp = client.post("/api/v1/load/batch-predict", json={
            "load_windows": [[50.0] * 24, [52.0] * 24],
            "horizon_hours": 1,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["predictions"]) == 2

    def test_predict_sequence_after_training(self, client):
        client.post("/api/v1/load/train", json={
            "load_values": [50.0, 52.0, 48.0, 51.0, 49.0, 53.0, 50.0, 48.0,
                           52.0, 51.0, 49.0, 50.0, 51.0, 48.0, 52.0, 50.0,
                           49.0, 51.0, 50.0, 48.0, 52.0, 51.0, 50.0, 49.0],
        })
        resp = client.post("/api/v1/load/predict-sequence", json={
            "recent_load": [50.0] * 24,
            "horizon_hours": 12,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["predictions"]) == 12


class TestFaultAPI:
    def test_detect_fault(self, client):
        resp = client.post("/api/v1/fault/detect", json={
            "sensor_reading": [230.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0],
            "enable_rules": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "anomaly_score" in data
        assert "detected_faults" in data
        assert "severity" in data

    def test_detect_batch_faults(self, client):
        resp = client.post("/api/v1/fault/detect-batch", json={
            "sensor_readings": [
                [230.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0],
                [270.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0],
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_readings"] == 2
        assert data["anomalies_detected"] >= 0

    def test_fault_status(self, client):
        resp = client.get("/api/v1/fault/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "model_type" in data
        assert data["model_type"] == "autoencoder"


class TestRenewableAPI:
    def test_forecast_renewable(self, client):
        resp = client.post("/api/v1/renewable/forecast", json={
            "historical_generation": [5.0, 6.0, 5.5, 7.0, 6.5, 8.0, 7.5, 9.0] * 3,
            "horizon_hours": 24,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["forecasted_generation_mw"]) == 24
        assert "baseline_mw" in data

    def test_optimize_dispatch(self, client):
        resp = client.post("/api/v1/renewable/optimize", json={
            "forecasted_load_mw": [50.0, 52.0, 48.0, 45.0, 44.0, 46.0, 50.0, 58.0, 65.0, 70.0, 72.0,
                                   70.0, 68.0, 65.0, 63.0, 62.0, 64.0, 68.0, 72.0, 70.0, 65.0, 58.0, 52.0, 50.0],
            "forecasted_renewable_mw": [0.5, 0.3, 0.2, 0.1, 0.1, 0.2, 0.5, 1.5, 3.0, 5.0, 7.0, 8.5,
                                        9.0, 8.5, 7.5, 6.0, 4.5, 3.0, 1.5, 0.8, 0.3, 0.1, 0.0, 0.0],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["horizon_hours"] == 24
        assert len(data["dispatch_plan"]) == 24
        assert "summary" in data
        assert "constraint_checks" in data

    def test_simulate_storage(self, client):
        resp = client.post("/api/v1/renewable/storage-simulate", json={
            "net_load_series": [10.0, -5.0, 15.0, -8.0, 12.0, -3.0],
            "initial_storage_mwh": 10.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "storage_trace_mwh" in data
        assert "final_storage_mwh" in data

    def test_carbon_impact(self, client):
        resp = client.post("/api/v1/renewable/carbon-impact", json={
            "renewable_used_mwh": 50.0,
            "grid_mwh": 30.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["carbon_saved_tonnes"] > 0

    def test_grid_status(self, client):
        resp = client.get("/api/v1/metrics/grid-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["grid_capacity_mw"] == 100.0


class TestAPIErrorHandling:
    def test_predict_load_invalid_horizon(self, client):
        resp = client.post("/api/v1/load/predict", json={
            "recent_load": [50.0] * 24,
            "horizon_hours": 999,
        })
        assert resp.status_code == 400

    def test_fault_detection_invalid_dims(self, client):
        resp = client.post("/api/v1/fault/detect", json={
            "sensor_reading": [1.0, 2.0, 3.0],
            "enable_rules": True,
        })
        assert resp.status_code == 200


class TestServiceLayer:
    def test_service_creation(self):
        from gridmind.services import create_service
        svc = create_service()
        assert svc.predictor is not None
        assert svc.detector is not None
        assert svc.integrator is not None

    def test_service_predict_load(self):
        from gridmind.services import create_service
        import numpy as np
        svc = create_service()
        load_data = np.array([50.0, 52.0, 48.0, 51.0, 49.0, 53.0, 50.0, 48.0,
                             52.0, 51.0, 49.0, 50.0, 51.0, 48.0, 52.0, 50.0,
                             49.0, 51.0, 50.0, 48.0, 52.0, 51.0, 50.0, 49.0])
        svc.predictor.fit(load_data, epochs=2)
        result = svc.predict_load([50.0] * 24, horizon_hours=1)
        assert result["predicted_load"] >= 0

    def test_service_detect_fault(self):
        from gridmind.services import create_service
        svc = create_service()
        result = svc.detect_faults([230.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0])
        assert "detected_faults" in result
