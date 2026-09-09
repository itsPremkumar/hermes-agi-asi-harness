"""Tests for GridMind Pydantic schemas."""

import datetime

import pytest

from gridmind import (
    LoadDataRequest,
    LoadForecastRequest,
    LoadForecastResponse,
    FaultDetectionRequest,
    FaultDetectionResponse,
    RenewableForecastRequest,
    DispatchRequest,
    CarbonImpactRequest,
    HealthResponse,
    BatchPredictRequest,
    BatchPredictResponse,
    FaultBatchRequest,
    FaultBatchResponse,
    RenewableForecastResponse,
    DispatchResponse,
    StorageSimulationRequest,
    StorageSimulationResponse,
    CarbonImpactResponse,
    ModelStatusResponse,
)


class TestLoadDataRequest:
    def test_valid_request(self):
        req = LoadDataRequest(load_values=[50.0, 52.0, 48.0])
        assert req.load_values == [50.0, 52.0, 48.0]
        assert req.timestamps is None

    def test_with_timestamps(self):
        ts = [datetime.datetime(2024, 1, 1, h, 0) for h in range(3)]
        req = LoadDataRequest(load_values=[50.0, 52.0, 48.0], timestamps=ts)
        assert len(req.timestamps) == 3

    def test_empty_load_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LoadDataRequest(load_values=[])


class TestLoadForecastRequest:
    def test_valid_default(self):
        req = LoadForecastRequest(recent_load=[50.0] * 24)
        assert req.horizon_hours == 1

    def test_valid_custom_horizon(self):
        req = LoadForecastRequest(recent_load=[50.0] * 24, horizon_hours=24)
        assert req.horizon_hours == 24

    def test_short_window_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LoadForecastRequest(recent_load=[50.0] * 10)

    def test_invalid_horizon_high(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LoadForecastRequest(recent_load=[50.0] * 24, horizon_hours=49)

    def test_invalid_horizon_zero(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            LoadForecastRequest(recent_load=[50.0] * 24, horizon_hours=0)


class TestFaultDetectionRequest:
    def test_valid(self):
        req = FaultDetectionRequest(sensor_reading=[230.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0])
        assert len(req.sensor_reading) == 8
        assert req.enable_rules is True

    def test_rules_disabled(self):
        req = FaultDetectionRequest(sensor_reading=[230.0] * 5, enable_rules=False)
        assert req.enable_rules is False

    def test_empty_rejected(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            FaultDetectionRequest(sensor_reading=[])


class TestSensorDataRequest:
    def test_valid(self):
        req = SensorDataRequest(sensor_values=[1.0, 2.0, 3.0])
        assert len(req.sensor_values) == 3
        assert req.sensor_names is None


class TestRenewableForecastRequest:
    def test_valid(self):
        req = RenewableForecastRequest(historical_generation=[5.0] * 24)
        assert req.horizon_hours == 24
        assert req.weather_forecast is None

    def test_with_weather(self):
        weather = {"cloud_cover_percent": 50, "wind_speed_ms": 5.0}
        req = RenewableForecastRequest(historical_generation=[5.0] * 24, weather_forecast=weather)
        assert req.weather_forecast["cloud_cover_percent"] == 50


class TestDispatchRequest:
    def test_valid(self):
        req = DispatchRequest(
            forecasted_load_mw=[50.0, 52.0, 48.0],
            forecasted_renewable_mw=[2.0, 3.0, 1.0],
        )
        assert len(req.forecasted_load_mw) == 3
        assert req.current_storage_mwh == 0.0

    def test_with_price(self):
        req = DispatchRequest(
            forecasted_load_mw=[50.0] * 3,
            forecasted_renewable_mw=[2.0] * 3,
            price_signal=[30.0, 35.0, 40.0],
        )
        assert req.price_signal == [30.0, 35.0, 40.0]

    def test_mismatched_lengths(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            DispatchRequest(
                forecasted_load_mw=[50.0, 52.0],
                forecasted_renewable_mw=[2.0],
            )


class TestStorageSimulationRequest:
    def test_valid(self):
        req = StorageSimulationRequest(net_load_series=[10.0, -5.0, 15.0])
        assert len(req.net_load_series) == 3
        assert req.initial_storage_mwh == 0.0
        assert req.price_aware is True


class TestCarbonImpactRequest:
    def test_valid_defaults(self):
        req = CarbonImpactRequest(renewable_used_mwh=50.0, grid_mwh=30.0)
        assert req.grid_carbon_intensity_gco2_per_kwh == 400.0
        assert req.renewable_carbon_intensity_gco2_per_kwh == 20.0

    def test_custom_intensity(self):
        req = CarbonImpactRequest(
            renewable_used_mwh=50.0,
            grid_mwh=30.0,
            grid_carbon_intensity_gco2_per_kwh=500.0,
            renewable_carbon_intensity_gco2_per_kwh=10.0,
        )
        assert req.grid_carbon_intensity_gco2_per_kwh == 500.0


class TestHealthResponse:
    def test_create(self):
        resp = HealthResponse(status="healthy", version="1.0.0", service="GridMind", timestamp="t")
        assert resp.status == "healthy"
        assert resp.version == "1.0.0"


class TestLoadForecastResponse:
    def test_create(self):
        resp = LoadForecastResponse(
            predicted_load=55.0,
            horizon_hours=1,
            model_type="lstm",
            timestamp="t",
        )
        assert resp.predicted_load == 55.0
        assert resp.confidence_interval is None

    def test_with_confidence(self):
        resp = LoadForecastResponse(
            predicted_load=55.0,
            horizon_hours=1,
            model_type="lstm",
            timestamp="t",
            confidence_interval={"lower": 50.0, "upper": 60.0, "level": 0.95},
        )
        assert resp.confidence_interval["level"] == 0.95


class TestFaultDetectionResponse:
    def test_create(self):
        resp = FaultDetectionResponse(
            timestamp="t",
            anomaly_score=0.5,
            threshold=0.8,
            is_anomaly=False,
            detected_faults=[],
            severity="normal",
            sensor_dims=8,
        )
        assert resp.is_anomaly is False
        assert resp.severity == "normal"


class TestRenewableForecastResponse:
    def test_create(self):
        resp = RenewableForecastResponse(
            horizon_hours=24,
            forecasted_generation_mw=[5.0] * 24,
            baseline_mw=5.0,
            mean_forecast_mw=5.0,
            total_forecast_mwh=120.0,
            weather_used=False,
            method="historical",
        )
        assert len(resp.forecasted_generation_mw) == 24


class TestDispatchResponse:
    def test_create(self):
        plan = [{"hour": 0, "load_mw": 50.0, "renewable_used_mw": 2.0, "storage_action": "idle"}]
        resp = DispatchResponse(
            horizon_hours=1,
            dispatch_plan=plan,
            storage_trace_mwh=[0.0],
            final_storage_level_mwh=0.0,
            summary={"total_load_mwh": 50.0},
            constraint_checks={"constraints_satisfied": True},
            timestamp="t",
        )
        assert resp.horizon_hours == 1


class TestStorageSimulationResponse:
    def test_create(self):
        resp = StorageSimulationResponse(
            initial_storage_mwh=0.0,
            final_storage_mwh=10.0,
            net_change_mwh=10.0,
            total_charged_mwh=10.0,
            total_discharged_mwh=0.0,
            storage_trace_mwh=[0.0, 5.0, 10.0],
            storage_utilization_percent=20.0,
            grid_events=[],
        )
        assert resp.final_storage_mwh == 10.0


class TestCarbonImpactResponse:
    def test_create(self):
        resp = CarbonImpactResponse(
            renewable_energy_mwh=50.0,
            grid_energy_mwh=30.0,
            renewable_co2_tonnes=1.0,
            grid_co2_tonnes=12.0,
            total_co2_tonnes=13.0,
            baseline_co2_tonnes=32.0,
            carbon_saved_tonnes=19.0,
            carbon_reduction_percent=59.38,
        )
        assert resp.carbon_saved_tonnes == 19.0


class TestBatchPredictResponse:
    def test_create(self):
        resp = BatchPredictResponse(predictions=[50.0, 52.0, 48.0], horizon_hours=1)
        assert len(resp.predictions) == 3


class TestFaultBatchResponse:
    def test_create(self):
        resp = FaultBatchResponse(
            total_readings=10,
            anomalies_detected=2,
            critical_count=0,
            anomaly_rate=0.2,
        )
        assert resp.anomaly_rate == 0.2
