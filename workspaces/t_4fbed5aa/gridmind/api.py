"""GridMind FastAPI router — all API endpoints."""

from __future__ import annotations

import numpy as np
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from gridmind import LoadPredictor, FaultDetector, RenewableIntegrator
from gridmind.config import get_settings
from gridmind.schemas import (
    BatchPredictRequest,
    BatchPredictResponse,
    CarbonImpactRequest,
    CarbonImpactResponse,
    DispatchRequest,
    DispatchResponse,
    FaultBatchRequest,
    FaultBatchResponse,
    FaultDetectionRequest,
    FaultDetectionResponse,
    HealthResponse,
    LoadDataRequest,
    LoadForecastRequest,
    LoadForecastResponse,
    LoadForecastSequenceResponse,
    ModelStatusResponse,
    RenewableForecastRequest,
    RenewableForecastResponse,
    SensorDataRequest,
    StorageSimulationRequest,
    StorageSimulationResponse,
)

router = APIRouter(prefix="/api/v1", tags=["gridmind"])


_predictor: LoadPredictor | None = None
_detector: FaultDetector | None = None
_integrator: RenewableIntegrator | None = None


def get_predictor() -> LoadPredictor:
    global _predictor
    if _predictor is None:
        _predictor = LoadPredictor()
    return _predictor


def get_detector() -> FaultDetector:
    global _detector
    if _detector is None:
        _detector = FaultDetector()
    return _detector


def get_integrator() -> RenewableIntegrator:
    global _integrator
    if _integrator is None:
        _integrator = RenewableIntegrator()
    return _integrator


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        service=settings.app_name,
        timestamp="",  # filled by response
    )


@router.get("/health/full", tags=["system"])
def full_health() -> dict[str, Any]:
    pred = get_predictor()
    det = get_detector()
    integ = get_integrator()
    return {
        "status": "healthy",
        "services": {
            "load_predictor": {"trained": pred.trained, "model_type": pred.model_type},
            "fault_detector": {"trained": det.trained, "model_type": "autoencoder"},
            "renewable_integrator": {"grid_capacity_mw": integ.grid_capacity_mw},
        },
    }


@router.post("/load/predict", response_model=LoadForecastResponse, tags=["load"])
def predict_load(req: LoadForecastRequest) -> LoadForecastResponse:
    pred = get_predictor()
    if not pred.trained:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Load prediction model not trained. Send load data to train first.",
        )
    try:
        result = pred.predict(req.recent_load, req.horizon_hours, confidence=True)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return LoadForecastResponse(**result)


@router.post("/load/predict-sequence", response_model=LoadForecastSequenceResponse, tags=["load"])
def predict_load_sequence(req: LoadForecastRequest) -> LoadForecastSequenceResponse:
    pred = get_predictor()
    if not pred.trained:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Load prediction model not trained.",
        )
    try:
        result = pred.predict_sequence(req.recent_load, req.horizon_hours)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return LoadForecastSequenceResponse(**result)


@router.post("/load/batch-predict", response_model=BatchPredictResponse, tags=["load"])
def batch_predict(req: BatchPredictRequest) -> BatchPredictResponse:
    pred = get_predictor()
    if not pred.trained:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Model not trained",
        )
    predictions: list[float] = []
    for window in req.load_windows:
        try:
            res = pred.predict(window, req.horizon_hours, confidence=False)
            predictions.append(res["predicted_load"])
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return BatchPredictResponse(predictions=predictions, horizon_hours=req.horizon_hours)


@router.post("/load/train", tags=["load"])
def train_load_model(req: LoadDataRequest) -> dict[str, Any]:
    pred = get_predictor()
    try:
        result = pred.fit(req.load_values)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    result["model_type"] = pred.model_type
    result["trained"] = pred.trained
    result["scaler_mean"] = pred.scaler_mean
    result["scaler_std"] = pred.scaler_std
    return result


@router.get("/load/evaluate", tags=["load"])
def evaluate_load(actual: list[float], predicted: list[float]) -> dict[str, Any]:
    pred = get_predictor()
    try:
        return pred.evaluate(actual, predicted)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/load/status", response_model=ModelStatusResponse, tags=["load"])
def load_model_status() -> ModelStatusResponse:
    pred = get_predictor()
    return ModelStatusResponse(
        model_type=pred.model_type,
        trained=pred.trained,
        scaler_mean=pred.scaler_mean,
        scaler_std=pred.scaler_std,
        epochs_trained=pred.history[-1]["epoch"] if pred.history else None,
        device=pred.device,
    )


@router.post("/fault/detect", response_model=FaultDetectionResponse, tags=["fault"])
def detect_fault(req: FaultDetectionRequest) -> FaultDetectionResponse:
    det = get_detector()
    if det.sensor_dims > 0 and len(req.sensor_reading) != det.sensor_dims:
        det.sensor_dims = len(req.sensor_reading)
    try:
        result = det.detect(req.sensor_reading, rules=req.enable_rules)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return FaultDetectionResponse(**result)


@router.post("/fault/detect-batch", response_model=FaultBatchResponse, tags=["fault"])
def detect_fault_batch(req: FaultBatchRequest) -> FaultBatchResponse:
    det = get_detector()
    if det.sensor_dims > 0 and len(req.sensor_readings[0]) != det.sensor_dims:
        det.sensor_dims = len(req.sensor_readings[0])
    try:
        result = det.detect_batch(req.sensor_readings)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return FaultBatchResponse(**result)


@router.post("/fault/train", tags=["fault"])
def train_fault_model(req: SensorDataRequest) -> dict[str, Any]:
    det = get_detector()
    sensor_arr = req.sensor_values if req.sensor_values else []
    if not sensor_arr:
        sensor_arr = [0.0] * det.sensor_dims
    if len(sensor_arr) == 0:
        sensor_arr = [0.0] * 10
    det.sensor_dims = len(sensor_arr)
    try:
        result = det.fit(np.array([sensor_arr]), val_split=0.0)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    result["model_type"] = "autoencoder"
    result["trained"] = det.trained
    result["threshold"] = det.threshold
    return result


@router.get("/fault/status", tags=["fault"])
def fault_model_status() -> dict[str, Any]:
    det = get_detector()
    return {
        "model_type": "autoencoder",
        "trained": det.trained,
        "threshold": round(det.threshold, 6) if det.trained else None,
        "sensor_dims": det.sensor_dims,
    }


@router.post("/renewable/forecast", response_model=RenewableForecastResponse, tags=["renewable"])
def forecast_renewable(req: RenewableForecastRequest) -> RenewableForecastResponse:
    integ = get_integrator()
    try:
        result = integ.forecast_renewable_generation(
            req.historical_generation,
            req.horizon_hours,
            req.weather_forecast,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return RenewableForecastResponse(
        horizon_hours=result["horizon_hours"],
        forecasted_generation_mw=result["forecasted_generation_mw"],
        baseline_mw=result["baseline_mw"],
        mean_forecast_mw=result["mean_forecast_mw"],
        total_forecast_mwh=result["total_forecast_mwh"],
        weather_used=result["weather_used"],
        method=result["method"],
    )


@router.post("/renewable/optimize", response_model=DispatchResponse, tags=["renewable"])
def optimize_dispatch(req: DispatchRequest) -> DispatchResponse:
    integ = get_integrator()
    try:
        result = integ.optimize_dispatch(
            req.forecasted_load_mw,
            req.forecasted_renewable_mw,
            req.current_storage_mwh,
            req.price_signal,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return DispatchResponse(
        horizon_hours=result["horizon_hours"],
        dispatch_plan=result["dispatch_plan"],
        storage_trace_mwh=result["storage_trace_mwh"],
        final_storage_level_mwh=result["final_storage_level_mwh"],
        summary=result["summary"],
        constraint_checks=result["constraint_checks"],
        timestamp=result["timestamp"],
    )


@router.post("/renewable/storage-simulate", response_model=StorageSimulationResponse, tags=["renewable"])
def simulate_storage(req: StorageSimulationRequest) -> StorageSimulationResponse:
    integ = get_integrator()
    try:
        result = integ.simulate_storage(req.net_load_series, req.initial_storage_mwh, req.price_aware)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return StorageSimulationResponse(
        initial_storage_mwh=result["initial_storage_mwh"],
        final_storage_mwh=result["final_storage_mwh"],
        net_change_mwh=result["net_change_mwh"],
        total_charged_mwh=result["total_charged_mwh"],
        total_discharged_mwh=result["total_discharged_mwh"],
        storage_trace_mwh=result["storage_trace_mwh"],
        storage_utilization_percent=result["storage_utilization_percent"],
        grid_events=result["grid_events"],
    )


@router.post("/renewable/carbon-impact", response_model=CarbonImpactResponse, tags=["renewable"])
def carbon_impact(req: CarbonImpactRequest) -> CarbonImpactResponse:
    integ = get_integrator()
    try:
        result = integ.compute_carbon_impact(
            req.renewable_used_mwh,
            req.grid_mwh,
            req.grid_carbon_intensity_gco2_per_kwh,
            req.renewable_carbon_intensity_gco2_per_kwh,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return CarbonImpactResponse(**result)


@router.get("/metrics/grid-status", tags=["metrics"])
def grid_status_summary() -> dict[str, Any]:
    integ = get_integrator()
    return {
        "grid_capacity_mw": integ.grid_capacity_mw,
        "storage_capacity_mwh": integ.storage_capacity_mwh,
        "storage_current_mwh": integ.storage_level_mwh,
        "storage_utilization_percent": round(
            integ.storage_level_mwh / max(integ.storage_capacity_mwh, 1e-8) * 100, 2
        ),
        "min_renewable_fraction": integ.min_renewable_fraction,
        "max_curtailment_percent": integ.max_curtailment_percent,
    }
