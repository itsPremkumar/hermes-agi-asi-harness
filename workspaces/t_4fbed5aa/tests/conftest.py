"""GridMind test configuration and fixtures."""

import numpy as np
import pytest

from gridmind import LoadPredictor, FaultDetector, RenewableIntegrator


@pytest.fixture
def load_predictor() -> LoadPredictor:
    """Provides a fresh LoadPredictor instance."""
    return LoadPredictor(
        model_type="lstm",
        hidden_size=32,
        num_layers=1,
        dropout=0.1,
        learning_rate=1e-3,
        epochs=5,
        batch_size=16,
        window_size=12,
    )


@pytest.fixture
def load_predictor_gru() -> LoadPredictor:
    """Provides a GRU-based LoadPredictor."""
    return LoadPredictor(
        model_type="gru",
        hidden_size=24,
        num_layers=1,
        dropout=0.1,
        learning_rate=1e-3,
        epochs=5,
        batch_size=16,
        window_size=12,
    )


@pytest.fixture
def fault_detector() -> FaultDetector:
    """Provides a fresh FaultDetector."""
    return FaultDetector(
        sensor_dims=8,
        latent_dim=8,
        encoder_hidden=(32, 16),
        learning_rate=1e-3,
        epochs=5,
        batch_size=32,
    )


@pytest.fixture
def renewable_integrator() -> RenewableIntegrator:
    """Provides a fresh RenewableIntegrator."""
    return RenewableIntegrator(
        grid_capacity_mw=100.0,
        storage_capacity_mwh=50.0,
        storage_charge_rate_mw=20.0,
        storage_discharge_rate_mw=20.0,
    )


@pytest.fixture
def synthetic_load_data() -> np.ndarray:
    """Generates realistic-looking synthetic load data with daily seasonality."""
    np.random.seed(42)
    hours = 240
    t = np.arange(hours)
    base_load = 50.0
    daily = 20.0 * np.sin(2 * np.pi * (t % 24 - 8) / 24)
    weekly = 5.0 * np.sin(2 * np.pi * t / (24 * 7))
    noise = np.random.normal(0, 3.0, hours)
    load = base_load + daily + weekly + noise
    return np.maximum(load, 10.0)


@pytest.fixture
def synthetic_sensor_data() -> np.ndarray:
    """Generates synthetic normal sensor data for fault detector training."""
    np.random.seed(123)
    n_samples = 500
    data = np.random.normal(loc=230.0, scale=5.0, size=(n_samples, 8))
    data[:, 1] = np.random.normal(50.0, 10.0, n_samples)
    data[:, 2] = np.random.normal(50.0, 0.1, n_samples)
    data[:, 3:6] = np.random.normal(225.0, 3.0, (n_samples, 3))
    data[:, 6] = np.random.normal(2.0, 0.5, n_samples)
    data[:, 7] = np.random.normal(45.0, 5.0, n_samples)
    return data


@pytest.fixture
def hourly_forecast_load() -> list[float]:
    """24-hour load forecast for dispatch tests."""
    return [55.0, 52.0, 48.0, 45.0, 44.0, 46.0, 50.0, 58.0, 65.0, 70.0, 72.0,
            70.0, 68.0, 65.0, 63.0, 62.0, 64.0, 68.0, 72.0, 70.0, 65.0, 58.0, 52.0, 50.0]


@pytest.fixture
def hourly_forecast_renewable() -> list[float]:
    """24-hour renewable forecast for dispatch tests."""
    return [0.5, 0.3, 0.2, 0.1, 0.1, 0.2, 0.5, 1.5, 3.0, 5.0, 7.0, 8.5,
            9.0, 8.5, 7.5, 6.0, 4.5, 3.0, 1.5, 0.8, 0.3, 0.1, 0.0, 0.0]
