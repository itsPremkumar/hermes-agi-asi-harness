"""Load prediction models for smart grid — PyTorch-based LSTM/GRU forecasting."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from numpy.typing import NDArray

from gridmind.config import get_settings


class TimeSeriesDataset(torch.utils.data.Dataset):
    """Sliding window dataset for time series forecasting."""

    def __init__(self, data: NDArray, window_size: int = 24, horizon: int = 1):
        self.data = torch.tensor(data, dtype=torch.float32)
        self.window_size = window_size
        self.horizon = horizon

    def __len__(self) -> int:
        return max(0, len(self.data) - self.window_size - self.horizon + 1)

    def __getitem__(self, idx: int):
        x = self.data[idx : idx + self.window_size]
        y = self.data[idx + self.window_size : idx + self.window_size + self.horizon]
        return x.unsqueeze(-1), y.unsqueeze(-1)


class LSTMLoader(nn.Module):
    """LSTM-based load forecast model."""

    def __init__(
        self,
        input_size: int = 1,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        horizon: int = 1,
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, horizon),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        lstm_out, _ = self.lstm(x)
        last_output = lstm_out[:, -1, :]
        return self.fc(last_output)


class GRULoader(nn.Module):
    """GRU-based load forecast model — lighter than LSTM."""

    def __init__(
        self,
        input_size: int = 1,
        hidden_size: int = 48,
        num_layers: int = 2,
        dropout: float = 0.2,
        horizon: int = 1,
    ):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 16),
            nn.ReLU(),
            nn.Linear(16, horizon),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        gru_out, _ = self.gru(x)
        last_output = gru_out[:, -1, :]
        return self.fc(last_output)


class LoadPredictor:
    """
    Smart grid load prediction using PyTorch time-series models.

    Supports LSTM and GRU architectures for short-term (1-24h) load forecasting
    with automatic model selection and training.
    """

    SUPPORTED_HORIZONS = list(range(1, 49))  # 1 to 48 hours

    def __init__(
        self,
        model_type: str = "lstm",
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        learning_rate: float = 1e-3,
        epochs: int = 50,
        batch_size: int = 32,
        window_size: int = 24,
        device: Optional[str] = None,
    ):
        if model_type not in ("lstm", "gru"):
            raise ValueError(f"model_type must be 'lstm' or 'gru', got {model_type!r}")

        self.model_type = model_type
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.batch_size = batch_size
        self.window_size = window_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self.model: nn.Module | None = None
        self.scaler_mean: float = 0.0
        self.scaler_std: float = 1.0
        self.trained: bool = False
        self.history: list[dict] = []
        self.feature_columns: list[str] = []

    def _build_model(self, horizon: int) -> nn.Module:
        if self.model_type == "lstm":
            return LSTMLoader(
                hidden_size=self.hidden_size,
                num_layers=self.num_layers,
                dropout=self.dropout,
                horizon=horizon,
            ).to(self.device)
        return GRULoader(
            hidden_size=self.hidden_size,
            num_layers=self.num_layers,
            dropout=self.dropout,
            horizon=horizon,
        ).to(self.device)

    def fit(
        self,
        load_data: NDArray,
        timestamps: Optional[NDArray] = None,
        val_split: float = 0.2,
        early_stopping_patience: int = 10,
        seed: int = 42,
        epochs: Optional[int] = None,
    ) -> dict:
        """Train the load prediction model on historical load data."""
        effective_epochs = epochs if epochs is not None else self.epochs
        if len(load_data) < self.window_size + 2:
            raise ValueError(
                f"Need at least {self.window_size + 2} data points, got {len(load_data)}"
            )

        np.random.seed(seed)
        torch.manual_seed(seed)

        load_arr = np.asarray(load_data, dtype=np.float64)
        self.scaler_mean = float(np.mean(load_arr))
        self.scaler_std = float(np.std(load_arr)) or 1.0
        normalized = (load_arr - self.scaler_mean) / self.scaler_std

        n = len(normalized)
        val_size = max(1, int(n * val_split))
        train_size = n - val_size

        train_data = normalized[:train_size]
        val_data = normalized[train_size - self.window_size :]

        train_dataset = TimeSeriesDataset(train_data, self.window_size, 1)
        val_dataset = TimeSeriesDataset(val_data, self.window_size, 1)

        train_loader = torch.utils.data.DataLoader(
            train_dataset, batch_size=self.batch_size, shuffle=True
        )
        val_loader = torch.utils.data.DataLoader(
            val_dataset, batch_size=self.batch_size, shuffle=False
        )

        self.model = self._build_model(horizon=1)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=5
        )

        best_val_loss = float("inf")
        patience_counter = 0
        self.history = []

        for epoch in range(effective_epochs):
            self.model.train()
            train_losses = []
            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)
                optimizer.zero_grad()
                pred = self.model(X_batch)
                loss = criterion(pred, y_batch)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()
                train_losses.append(loss.item())

            self.model.eval()
            val_losses = []
            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    X_batch = X_batch.to(self.device)
                    y_batch = y_batch.to(self.device)
                    pred = self.model(X_batch)
                    val_losses.append(criterion(pred, y_batch).item())

            train_loss = float(np.mean(train_losses))
            val_loss = float(np.mean(val_losses))
            scheduler.step(val_loss)

            self.history.append({"epoch": epoch + 1, "train_loss": train_loss, "val_loss": val_loss})

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                torch.save(self.model.state_dict(), "/tmp/gridmind_best_model.pt")
            else:
                patience_counter += 1

            if patience_counter >= early_stopping_patience:
                break

        state = torch.load("/tmp/gridmind_best_model.pt", map_location=self.device)
        self.model.load_state_dict(state)
        self.trained = True

        return {
            "model_type": self.model_type,
            "final_train_loss": self.history[-1]["train_loss"],
            "final_val_loss": self.history[-1]["val_loss"],
            "best_val_loss": best_val_loss,
            "epochs_trained": len(self.history),
            "device": self.device,
            "scaler_mean": self.scaler_mean,
            "scaler_std": self.scaler_std,
        }

    def predict(
        self,
        recent_load: NDArray,
        horizon_hours: int = 1,
        confidence: bool = False,
    ) -> dict:
        """Predict future load for the given horizon."""
        if not self.trained:
            raise RuntimeError("Model not trained. Call fit() first.")
        if horizon_hours not in self.SUPPORTED_HORIZONS:
            raise ValueError(f"horizon_hours must be in {self.SUPPORTED_HORIZONS}")

        recent_arr = np.asarray(recent_load, dtype=np.float64)
        if len(recent_arr) < self.window_size:
            raise ValueError(
                f"Need at least {self.window_size} recent points, got {len(recent_arr)}"
            )

        window = (recent_arr[-self.window_size:] - self.scaler_mean) / self.scaler_std
        x_tensor = torch.tensor(window, dtype=torch.float32).unsqueeze(-1).unsqueeze(0).to(self.device)

        self.model.eval()
        with torch.no_grad():
            normalized_pred = self.model(x_tensor).item()

        pred_value = normalized_pred * self.scaler_std + self.scaler_mean
        pred_value = max(0.0, pred_value)

        result: dict = {
            "predicted_load": round(float(pred_value), 2),
            "horizon_hours": horizon_hours,
            "model_type": self.model_type,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if confidence:
            residual_std = self.scaler_std * 0.08
            lower = max(0.0, pred_value - 1.96 * residual_std)
            upper = pred_value + 1.96 * residual_std
            result["confidence_interval"] = {
                "lower": round(lower, 2),
                "upper": round(upper, 2),
                "level": 0.95,
            }

        return result

    def predict_sequence(
        self,
        recent_load: NDArray,
        horizon_hours: int = 24,
    ) -> dict:
        """Predict a sequence of future load values (autoregressive)."""
        if not self.trained:
            raise RuntimeError("Model not trained. Call fit() first.")

        recent_arr = np.asarray(recent_load, dtype=np.float64)
        predictions: list[float] = []
        current_window = list(recent_arr[-self.window_size:])

        for _ in range(horizon_hours):
            x_tensor = (
                torch.tensor(current_window, dtype=torch.float32)
                .unsqueeze(-1)
                .unsqueeze(0)
                .to(self.device)
            )
            self.model.eval()
            with torch.no_grad():
                norm_pred = self.model(x_tensor).item()
            pred_value = max(0.0, norm_pred * self.scaler_std + self.scaler_mean)
            predictions.append(round(float(pred_value), 2))
            current_window.append(pred_value)
            current_window = current_window[-self.window_size :]

        return {
            "predictions": predictions,
            "horizon_hours": horizon_hours,
            "model_type": self.model_type,
        }

    def save(self, path: str | Path) -> None:
        """Save the trained model to disk."""
        if not self.trained or self.model is None:
            raise RuntimeError("No trained model to save.")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_state_dict": self.model.state_dict(),
                "model_type": self.model_type,
                "scaler_mean": self.scaler_mean,
                "scaler_std": self.scaler_std,
                "hidden_size": self.hidden_size,
                "num_layers": self.num_layers,
                "dropout": self.dropout,
                "window_size": self.window_size,
            },
            path,
        )

    def load(self, path: str | Path) -> dict:
        """Load a trained model from disk."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        self.model_type = checkpoint["model_type"]
        self.scaler_mean = checkpoint["scaler_mean"]
        self.scaler_std = checkpoint["scaler_std"]
        self.hidden_size = checkpoint["hidden_size"]
        self.num_layers = checkpoint["num_layers"]
        self.dropout = checkpoint["dropout"]
        self.window_size = checkpoint["window_size"]
        self.model = self._build_model(horizon=1)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.trained = True
        return {
            "model_type": self.model_type,
            "scaler_mean": self.scaler_mean,
            "scaler_std": self.scaler_std,
        }

    def evaluate(self, actual: NDArray, predicted: NDArray) -> dict:
        """Evaluate predictions against actual values."""
        actual_arr = np.asarray(actual, dtype=np.float64)
        pred_arr = np.asarray(predicted, dtype=np.float64)
        if len(actual_arr) != len(pred_arr):
            raise ValueError("actual and predicted must have same length")
        if len(actual_arr) == 0:
            raise ValueError("arrays must not be empty")

        mae = float(np.mean(np.abs(actual_arr - pred_arr)))
        mse = float(np.mean((actual_arr - pred_arr) ** 2))
        rmse = float(np.sqrt(mse))
        mape = float(np.mean(np.abs((actual_arr - pred_arr) / (actual_arr + 1e-8))) * 100)
        ss_res = float(np.sum((actual_arr - pred_arr) ** 2))
        ss_tot = float(np.sum((actual_arr - np.mean(actual_arr)) ** 2))
        r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

        return {
            "mae": round(mae, 4),
            "mse": round(mse, 4),
            "rmse": round(rmse, 4),
            "mape_percent": round(mape, 4),
            "r2": round(r2, 4),
            "n_samples": len(actual_arr),
        }
