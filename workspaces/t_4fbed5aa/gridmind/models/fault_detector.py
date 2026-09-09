"""Fault detection models for smart grid — anomaly and fault identification."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from numpy.typing import NDArray

from gridmind.config import get_settings


class FaultType(Enum):
    """Enumeration of detectable fault types."""
    NONE = "none"
    OVER_VOLTAGE = "over_voltage"
    UNDER_VOLTAGE = "under_voltage"
    OVER_CURRENT = "over_current"
    UNDER_CURRENT = "under_current"
    FREQUENCY_DRIFT = "frequency_drift"
    PHASE_IMBALANCE = "phase_imbalance"
    HARMONIC_DISTORTION = "harmonic_distortion"
    TEMPERATURE_ANomaly = "temperature_anomaly"
    COMBINED = "combined"


class AutoEncoder(nn.Module):
    """Autoencoder for anomaly detection in grid sensor data."""

    def __init__(
        self,
        input_dim: int,
        encoder_hidden: tuple[int, ...] = (64, 32),
        latent_dim: int = 16,
        decoder_hidden: tuple[int, ...] = (32, 64),
        dropout: float = 0.1,
    ):
        super().__init__()
        encoder_layers = []
        prev_dim = input_dim
        for h in encoder_hidden:
            encoder_layers.extend([
                nn.Linear(prev_dim, h),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            prev_dim = h
        encoder_layers.append(nn.Linear(prev_dim, latent_dim))
        self.encoder = nn.Sequential(*encoder_layers)

        decoder_layers = []
        prev_dim = latent_dim
        for h in decoder_hidden:
            decoder_layers.extend([
                nn.Linear(prev_dim, h),
                nn.ReLU(),
                nn.Dropout(dropout),
            ])
            prev_dim = h
        decoder_layers.append(nn.Linear(prev_dim, input_dim))
        self.decoder = nn.Sequential(*decoder_layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        latent = self.encoder(x)
        reconstructed = self.decoder(latent)
        return reconstructed


class FaultDetector:
    """
    Fault and anomaly detection for smart grid sensor streams.

    Uses an autoencoder reconstruction-error approach combined with threshold-based
    rule detection for known fault patterns.
    """

    def __init__(
        self,
        sensor_dims: int = 10,
        latent_dim: int = 16,
        encoder_hidden: tuple[int, ...] = (64, 32),
        learning_rate: float = 1e-3,
        epochs: int = 50,
        batch_size: int = 64,
        anomaly_threshold_percentile: float = 95.0,
        device: Optional[str] = None,
    ):
        self.sensor_dims = sensor_dims
        self.latent_dim = latent_dim
        self.encoder_hidden = encoder_hidden
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.anomaly_threshold_percentile = anomaly_threshold_percentile
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.model: Optional[AutoEncoder] = None
        self.threshold: float = 0.0
        self.trained: bool = False
        self.reconstruction_errors: list[float] = []

    def _build_model(self) -> AutoEncoder:
        return AutoEncoder(
            input_dim=self.sensor_dims,
            encoder_hidden=self.encoder_hidden,
            latent_dim=self.latent_dim,
        ).to(self.device)

    def fit(
        self,
        sensor_data: NDArray,
        val_split: float = 0.1,
        seed: int = 42,
    ) -> dict:
        """Train the autoencoder on normal (non-fault) sensor data."""
        if sensor_data.ndim != 2:
            raise ValueError(f"sensor_data must be 2D, got shape {sensor_data.shape}")
        if sensor_data.shape[1] != self.sensor_dims:
            raise ValueError(
                f"Expected {self.sensor_dims} sensor dims, got {sensor_data.shape[1]}"
            )
        if len(sensor_data) < 100:
            raise ValueError("Need at least 100 samples to train")

        np.random.seed(seed)
        torch.manual_seed(seed)

        data_tensor = torch.tensor(sensor_data, dtype=torch.float32).to(self.device)
        n = len(sensor_data)
        val_size = max(1, int(n * val_split))
        train_size = n - val_size

        train_dataset = torch.utils.data.TensorDataset(data_tensor[:train_size])
        val_dataset = torch.utils.data.TensorDataset(data_tensor[train_size:])
        train_loader = torch.utils.data.DataLoader(
            train_dataset, batch_size=self.batch_size, shuffle=True
        )
        val_loader = torch.utils.data.DataLoader(
            val_dataset, batch_size=self.batch_size, shuffle=False
        )

        self.model = self._build_model()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        criterion = nn.MSELoss()

        self.model.train()
        for epoch in range(self.epochs):
            train_losses = []
            for (batch,) in train_loader:
                optimizer.zero_grad()
                recon = self.model(batch)
                loss = criterion(recon, batch)
                loss.backward()
                optimizer.step()
                train_losses.append(loss.item())
            avg_train = float(np.mean(train_losses))

            self.model.eval()
            val_losses = []
            with torch.no_grad():
                for (batch,) in val_loader:
                    recon = self.model(batch)
                    val_losses.append(criterion(recon, batch).item())
            avg_val = float(np.mean(val_losses))
            self.reconstruction_errors.append(avg_val)

        self.model.eval()
        all_recon_errors = []
        with torch.no_grad():
            for (batch,) in torch.utils.data.DataLoader(
                torch.utils.data.TensorDataset(data_tensor), batch_size=self.batch_size
            ):
                recon = self.model(batch[0])
                errors = torch.mean((batch[0] - recon) ** 2, dim=1)
                all_recon_errors.extend(errors.cpu().tolist())

        self.threshold = float(np.percentile(all_recon_errors, self.anomaly_threshold_percentile))
        self.trained = True

        return {
            "model_type": "autoencoder",
            "final_train_loss": self.reconstruction_errors[-1] if self.reconstruction_errors else 0.0,
            "threshold": round(self.threshold, 6),
            "epochs_trained": self.epochs,
            "device": self.device,
            "sensor_dims": self.sensor_dims,
        }

    def detect(
        self,
        sensor_reading: NDArray,
        rules: bool = True,
    ) -> dict:
        """Detect faults in a single sensor reading."""
        reading = np.asarray(sensor_reading, dtype=np.float64)
        if reading.ndim == 1:
            reading = reading.reshape(1, -1)
        if reading.shape[1] != self.sensor_dims:
            raise ValueError(
                f"Expected {self.sensor_dims} sensor dims, got {reading.shape[1]}"
            )

        detected_faults: list[str] = []
        anomaly_score: float = 0.0

        if self.trained and self.model is not None:
            x = torch.tensor(reading, dtype=torch.float32).to(self.device)
            self.model.eval()
            with torch.no_grad():
                recon = self.model(x)
                per_sample_error = torch.mean((x - recon) ** 2, dim=1).item()
                anomaly_score = float(per_sample_error)
                if anomaly_score > self.threshold:
                    detected_faults.append("anomaly_autoencoder")

        if rules:
            rule_faults = self._rule_based_detection(reading)
            for f in rule_faults:
                if f.value not in detected_faults:
                    detected_faults.append(f.value)

        severity = "critical" if len(detected_faults) >= 2 else (
            "warning" if detected_faults else "normal"
        )

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "anomaly_score": round(anomaly_score, 6),
            "threshold": round(self.threshold, 6),
            "is_anomaly": anomaly_score > self.threshold,
            "detected_faults": detected_faults,
            "severity": severity,
            "sensor_dims": self.sensor_dims,
        }

    def _rule_based_detection(self, reading: NDArray) -> list[FaultType]:
        """Rule-based detection of known fault signatures."""
        faults: list[FaultType] = []
        flat = reading.flatten()

        if len(flat) >= 1:
            v = flat[0]
            if v > 260.0:
                faults.append(FaultType.OVER_VOLTAGE)
            elif v < 210.0:
                faults.append(FaultType.UNDER_VOLTAGE)

        if len(flat) >= 2:
            i = flat[1]
            if i > 120.0:
                faults.append(FaultType.OVER_CURRENT)
            elif i < 5.0:
                faults.append(FaultType.UNDER_CURRENT)

        if len(flat) >= 3:
            freq = flat[2]
            if abs(freq - 50.0) > 0.5:
                faults.append(FaultType.FREQUENCY_DRIFT)

        if len(flat) >= 4:
            phases = flat[3:6] if len(flat) >= 6 else flat[3:4]
            if len(phases) >= 2 and np.std(phases) > 15.0:
                faults.append(FaultType.PHASE_IMBALANCE)

        if len(flat) >= 7:
            harmonic = flat[6]
            if harmonic > 5.0:
                faults.append(FaultType.HARMONIC_DISTORTION)

        if len(flat) >= 8:
            temp = flat[7]
            if temp > 85.0:
                faults.append(FaultType.TEMPERATURE_ANomaly)

        if len(faults) >= 2:
            if FaultType.COMBINED not in faults:
                faults.append(FaultType.COMBINED)

        return faults

    def detect_batch(
        self,
        sensor_readings: NDArray,
    ) -> dict:
        """Detect faults in a batch of sensor readings."""
        readings = np.asarray(sensor_readings, dtype=np.float64)
        if readings.ndim == 1:
            readings = readings.reshape(-1, self.sensor_dims)
        if readings.shape[1] != self.sensor_dims:
            raise ValueError(
                f"Expected {self.sensor_dims} sensor dims, got {readings.shape[1]}"
            )

        results = [self.detect(r, rules=True) for r in readings]
        anomalies = sum(1 for r in results if r["is_anomaly"])
        critical = sum(1 for r in results if r["severity"] == "critical")

        return {
            "total_readings": len(readings),
            "anomalies_detected": anomalies,
            "critical_count": critical,
            "anomaly_rate": round(anomalies / len(readings), 4),
            "results": results,
        }

    def save(self, path: str | Path) -> None:
        if not self.trained or self.model is None:
            raise RuntimeError("No trained model to save.")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "sensor_dims": self.sensor_dims,
                "latent_dim": self.latent_dim,
                "encoder_hidden": self.encoder_hidden,
                "threshold": self.threshold,
            },
            path,
        )

    def load(self, path: str | Path) -> dict:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        self.sensor_dims = checkpoint["sensor_dims"]
        self.latent_dim = checkpoint["latent_dim"]
        self.encoder_hidden = checkpoint["encoder_hidden"]
        self.threshold = checkpoint["threshold"]
        self.model = self._build_model()
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.trained = True
        return {
            "sensor_dims": self.sensor_dims,
            "threshold": self.threshold,
        }
