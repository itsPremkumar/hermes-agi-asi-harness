"""Data schemas and Pydantic models for GridMind API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LoadDataRequest(BaseModel):
    load_values: list[float] = Field(..., min_length=1, description="Historical load values in MW")
    timestamps: list[datetime] | None = Field(None, description="Optional timestamps for each value")


class LoadForecastRequest(BaseModel):
    recent_load: list[float] = Field(..., min_length=24, description="Last 24+ hours of load data")
    horizon_hours: int = Field(default=1, ge=1, le=48, description="Forecast horizon in hours")


class LoadForecastResponse(BaseModel):
    predicted_load: float
    horizon_hours: int
    model_type: str
    timestamp: str
    confidence_interval: dict[str, float] | None = None


class LoadForecastSequenceResponse(BaseModel):
    predictions: list[float]
    horizon_hours: int
    model_type: str


class BatchPredictRequest(BaseModel):
    load_windows: list[list[float]] = Field(..., min_length=1, description="Multiple windows for batch prediction")
    horizon_hours: int = Field(default=1, ge=1, le=48)


class BatchPredictResponse(BaseModel):
    predictions: list[float]
    horizon_hours: int


class SensorDataRequest(BaseModel):
    sensor_values: list[float] = Field(..., min_length=1, description="Sensor readings")
    sensor_names: list[str] | None = Field(None, description="Optional sensor names")


class FaultDetectionRequest(BaseModel):
    sensor_reading: list[float] = Field(..., min_length=1, description="Current sensor reading vector")
    enable_rules: bool = Field(default=True, description="Enable rule-based detection")


class FaultDetectionResponse(BaseModel):
    timestamp: str
    anomaly_score: float
    threshold: float
    is_anomaly: bool
    detected_faults: list[str]
    severity: str
    sensor_dims: int


class FaultBatchRequest(BaseModel):
    sensor_readings: list[list[float]] = Field(..., min_length=1, description="Batch of sensor readings")


class FaultBatchResponse(BaseModel):
    total_readings: int
    anomalies_detected: int
    critical_count: int
    anomaly_rate: float


class RenewableForecastRequest(BaseModel):
    historical_generation: list[float] = Field(..., min_length=1, description="Historical renewable generation (MW)")
    horizon_hours: int = Field(default=24, ge=1, le=168)
    weather_forecast: dict[str, float] | None = Field(None, description="Optional weather data")


class RenewableForecastResponse(BaseModel):
    horizon_hours: int
    forecasted_generation_mw: list[float]
    baseline_mw: float
    mean_forecast_mw: float
    total_forecast_mwh: float
    weather_used: bool
    method: str


class DispatchRequest(BaseModel):
    forecasted_load_mw: list[float] = Field(..., min_length=1, description="Load forecast per hour (MW)")
    forecasted_renewable_mw: list[float] = Field(..., min_length=1, description="Renewable forecast per hour (MW)")
    current_storage_mwh: float = Field(default=0.0, ge=0.0)
    price_signal: list[float] | None = Field(None, description="Optional price signal per hour")


class DispatchResponse(BaseModel):
    horizon_hours: int
    dispatch_plan: list[dict[str, Any]]
    storage_trace_mwh: list[float]
    final_storage_level_mwh: float
    summary: dict[str, float]
    constraint_checks: dict[str, Any]
    timestamp: str


class StorageSimulationRequest(BaseModel):
    net_load_series: list[float] = Field(..., min_length=1, description="Net load time series")
    initial_storage_mwh: float = Field(default=0.0, ge=0.0)
    price_aware: bool = Field(default=True)


class StorageSimulationResponse(BaseModel):
    initial_storage_mwh: float
    final_storage_mwh: float
    net_change_mwh: float
    total_charged_mwh: float
    total_discharged_mwh: float
    storage_trace_mwh: list[float]
    storage_utilization_percent: float
    grid_events: list[dict[str, Any]]


class CarbonImpactRequest(BaseModel):
    renewable_used_mwh: float = Field(ge=0.0, description="Renewable energy used (MWh)")
    grid_mwh: float = Field(ge=0.0, description="Grid energy used (MWh)")
    grid_carbon_intensity_gco2_per_kwh: float = Field(default=400.0, ge=0.0)
    renewable_carbon_intensity_gco2_per_kwh: float = Field(default=20.0, ge=0.0)


class CarbonImpactResponse(BaseModel):
    renewable_energy_mwh: float
    grid_energy_mwh: float
    renewable_co2_tonnes: float
    grid_co2_tonnes: float
    total_co2_tonnes: float
    baseline_co2_tonnes: float
    carbon_saved_tonnes: float
    carbon_reduction_percent: float


class ModelStatusResponse(BaseModel):
    model_type: str
    trained: bool
    scaler_mean: float
    scaler_std: float
    epochs_trained: int | None = None
    device: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    service: str
    timestamp: str
