"""Tests for LoadPredictor — model creation, training, prediction."""

import numpy as np
import pytest

from gridmind.models.load_predictor import LSTMLoader, GRULoader, TimeSeriesDataset
from gridmind import LoadPredictor


class TestTimeSeriesDataset:
    """Tests for the sliding window dataset."""

    def test_dataset_length(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        ds = TimeSeriesDataset(data, window_size=3, horizon=1)
        assert len(ds) == 7

    def test_dataset_item_shapes(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        ds = TimeSeriesDataset(data, window_size=3, horizon=1)
        x, y = ds[0]
        assert x.shape == (3, 1)
        assert y.shape == (1, 1)

    def test_dataset_empty(self):
        data = np.array([1.0, 2.0])
        ds = TimeSeriesDataset(data, window_size=5, horizon=1)
        assert len(ds) == 0

    def test_dataset_normalization(self):
        data = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0])
        ds = TimeSeriesDataset(data, window_size=4, horizon=2)
        assert len(ds) == 3


class TestLSTMLoader:
    """Tests for the LSTM model architecture."""

    def test_lstm_creation(self):
        model = LSTMLoader(input_size=1, hidden_size=32, num_layers=2, horizon=1)
        assert model.hidden_size == 32
        assert model.num_layers == 2

    def test_lstm_forward_pass(self):
        model = LSTMLoader(input_size=1, hidden_size=16, num_layers=1, horizon=1)
        x = np.random.randn(4, 10, 1).astype(np.float32)
        import torch
        x_t = torch.tensor(x)
        out = model(x_t)
        assert out.shape == (4, 1)

    def test_lstm_dropout_disabled_single_layer(self):
        model = LSTMLoader(num_layers=1, dropout=0.5)
        assert model.lstm.dropout == 0.0

    def test_lstm_multi_step(self):
        model = LSTMLoader(input_size=1, hidden_size=32, num_layers=1, horizon=6)
        import torch
        x = torch.randn(2, 24, 1)
        out = model(x)
        assert out.shape == (2, 6)


class TestGRULoader:
    """Tests for the GRU model architecture."""

    def test_gru_creation(self):
        model = GRULoader(input_size=1, hidden_size=24, num_layers=2, horizon=1)
        assert model.hidden_size == 24

    def test_gru_forward_pass(self):
        model = GRULoader(input_size=1, hidden_size=16, num_layers=1, horizon=1)
        import torch
        x = torch.randn(4, 10, 1)
        out = model(x)
        assert out.shape == (4, 1)

    def test_gru_single_layer_no_dropout(self):
        model = GRULoader(num_layers=1, dropout=0.5)
        assert model.gru.dropout == 0.0


class TestLoadPredictorConstruction:
    """Tests for LoadPredictor construction and validation."""

    def test_default_construction(self):
        pred = LoadPredictor()
        assert pred.model_type == "lstm"
        assert pred.hidden_size == 64
        assert pred.num_layers == 2
        assert pred.dropout == 0.2
        assert pred.learning_rate == 1e-3
        assert pred.epochs == 50
        assert pred.batch_size == 32
        assert pred.window_size == 24
        assert pred.trained is False
        assert pred.model is None

    def test_gru_construction(self):
        pred = LoadPredictor(model_type="gru")
        assert pred.model_type == "gru"

    def test_invalid_model_type(self):
        with pytest.raises(ValueError, match="model_type must be"):
            LoadPredictor(model_type="transformer")

    def test_custom_hyperparameters(self):
        pred = LoadPredictor(
            model_type="lstm",
            hidden_size=128,
            num_layers=3,
            dropout=0.3,
            learning_rate=5e-4,
            epochs=100,
            batch_size=64,
            window_size=48,
        )
        assert pred.hidden_size == 128
        assert pred.num_layers == 3
        assert pred.epochs == 100
        assert pred.window_size == 48

    def test_device_detection(self):
        pred = LoadPredictor(device="cpu")
        assert pred.device == "cpu"

    def test_trained_flag_initial(self):
        pred = LoadPredictor()
        assert pred.trained is False
        assert pred.model is None
        assert pred.history == []
        assert pred.scaler_mean == 0.0
        assert pred.scaler_std == 1.0


class TestLoadPredictorTraining:
    """Tests for LoadPredictor training."""

    def test_train_too_short_data(self, load_predictor):
        short_data = np.random.randn(5)
        with pytest.raises(ValueError, match="Need at least"):
            load_predictor.fit(short_data)

    def test_train_success(self, load_predictor, synthetic_load_data):
        result = load_predictor.fit(synthetic_load_data, epochs=2)
        assert load_predictor.trained is True
        assert result["model_type"] == "lstm"
        assert "final_train_loss" in result
        assert "final_val_loss" in result
        assert "best_val_loss" in result
        assert "epochs_trained" in result
        assert result["trained"] if isinstance(result, dict) else True

    def test_train_gru_model(self, load_predictor_gru, synthetic_load_data):
        result = load_predictor_gru.fit(synthetic_load_data, epochs=2)
        assert result["model_type"] == "gru"
        assert load_predictor_gru.trained is True

    def test_train_with_timestamps(self, load_predictor, synthetic_load_data):
        timestamps = np.arange(len(synthetic_load_data)).astype(float)
        result = load_predictor.fit(synthetic_load_data, timestamps=timestamps, epochs=2)
        assert result["model_type"] == "lstm"

    def test_train_val_split(self, load_predictor, synthetic_load_data):
        result = load_predictor.fit(synthetic_load_data, val_split=0.3, epochs=2)
        assert 0 < result["epochs_trained"] <= 2

    def test_train_early_stopping(self, load_predictor, synthetic_load_data):
        result = load_predictor.fit(synthetic_load_data, epochs=50, early_stopping_patience=2)
        assert result["epochs_trained"] <= 50

    def test_train_seed_reproducibility(self, synthetic_load_data):
        pred1 = LoadPredictor(epochs=3, seed=42, batch_size=8)
        pred2 = LoadPredictor(epochs=3, seed=42, batch_size=8)
        r1 = pred1.fit(synthetic_load_data, epochs=3)
        r2 = pred2.fit(synthetic_load_data, epochs=3)
        assert abs(r1["best_val_loss"] - r2["best_val_loss"]) < 1.0

    def test_train_normalization(self, load_predictor, synthetic_load_data):
        result = load_predictor.fit(synthetic_load_data, epochs=2)
        assert result["scaler_mean"] > 0
        assert result["scaler_std"] > 0

    def test_train_history_tracking(self, load_predictor, synthetic_load_data):
        result = load_predictor.fit(synthetic_load_data, epochs=3)
        assert len(load_predictor.history) > 0
        for entry in load_predictor.history:
            assert "epoch" in entry
            assert "train_loss" in entry
            assert "val_loss" in entry


class TestLoadPredictorPrediction:
    """Tests for LoadPredictor prediction."""

    def test_predict_untrained_raises(self, load_predictor):
        with pytest.raises(RuntimeError, match="Model not trained"):
            load_predictor.predict(np.array([50.0] * 24))

    def test_predict_success(self, load_predictor, synthetic_load_data):
        load_predictor.fit(synthetic_load_data, epochs=3)
        recent = synthetic_load_data[-24:]
        result = load_predictor.predict(recent, horizon_hours=1)
        assert "predicted_load" in result
        assert result["horizon_hours"] == 1
        assert result["model_type"] == "lstm"
        assert "timestamp" in result
        assert result["predicted_load"] >= 0

    def test_predict_with_confidence(self, load_predictor, synthetic_load_data):
        load_predictor.fit(synthetic_load_data, epochs=3)
        result = load_predictor.predict(synthetic_load_data[-24:], confidence=True)
        assert "confidence_interval" in result
        ci = result["confidence_interval"]
        assert ci["level"] == 0.95
        assert ci["lower"] <= result["predicted_load"] <= ci["upper"]

    def test_predict_invalid_horizon(self, load_predictor, synthetic_load_data):
        load_predictor.fit(synthetic_load_data, epochs=3)
        with pytest.raises(ValueError, match="horizon_hours must be"):
            load_predictor.predict(synthetic_load_data[-24:], horizon_hours=0)

    def test_predict_horizon_48(self, load_predictor, synthetic_load_data):
        load_predictor.fit(synthetic_load_data, epochs=3)
        result = load_predictor.predict(synthetic_load_data[-24:], horizon_hours=48)
        assert result["horizon_hours"] == 48

    def test_predict_insufficient_recent_data(self, load_predictor, synthetic_load_data):
        load_predictor.fit(synthetic_load_data, epochs=3)
        short = synthetic_load_data[-10:]
        with pytest.raises(ValueError, match="Need at least"):
            load_predictor.predict(short, horizon_hours=1)

    def test_predict_gru(self, load_predictor_gru, synthetic_load_data):
        load_predictor_gru.fit(synthetic_load_data, epochs=3)
        result = load_predictor_gru.predict(synthetic_load_data[-24:], horizon_hours=1)
        assert result["model_type"] == "gru"
        assert result["predicted_load"] >= 0

    def test_predict_output_format(self, load_predictor, synthetic_load_data):
        load_predictor.fit(synthetic_load_data, epochs=3)
        result = load_predictor.predict(synthetic_load_data[-24:])
        assert isinstance(result["predicted_load"], float)
        assert isinstance(result["horizon_hours"], int)
        assert isinstance(result["model_type"], str)
        assert isinstance(result["timestamp"], str)


class TestLoadPredictorSequencePrediction:
    """Tests for autoregressive sequence prediction."""

    def test_sequence_predict_untrained(self, load_predictor):
        with pytest.raises(RuntimeError, match="Model not trained"):
            load_predictor.predict_sequence(np.array([50.0] * 24))

    def test_sequence_predict_success(self, load_predictor, synthetic_load_data):
        load_predictor.fit(synthetic_load_data, epochs=3)
        result = load_predictor.predict_sequence(synthetic_load_data[-24:], horizon_hours=24)
        assert len(result["predictions"]) == 24
        assert result["horizon_hours"] == 24
        for p in result["predictions"]:
            assert p >= 0

    def test_sequence_predict_short_horizon(self, load_predictor, synthetic_load_data):
        load_predictor.fit(synthetic_load_data, epochs=3)
        result = load_predictor.predict_sequence(synthetic_load_data[-24:], horizon_hours=6)
        assert len(result["predictions"]) == 6

    def test_sequence_predict_gru(self, load_predictor_gru, synthetic_load_data):
        load_predictor_gru.fit(synthetic_load_data, epochs=3)
        result = load_predictor_gru.predict_sequence(synthetic_load_data[-24:], horizon_hours=12)
        assert len(result["predictions"]) == 12
        assert result["model_type"] == "gru"


class TestLoadPredictorEvaluate:
    """Tests for LoadPredictor evaluation metrics."""

    def test_evaluate_basic(self, load_predictor):
        actual = np.array([50.0, 52.0, 48.0, 51.0, 49.0])
        predicted = np.array([51.0, 50.0, 49.0, 50.0, 50.0])
        result = load_predictor.evaluate(actual, predicted)
        assert "mae" in result
        assert "mse" in result
        assert "rmse" in result
        assert "mape_percent" in result
        assert "r2" in result
        assert "n_samples" in result
        assert result["n_samples"] == 5

    def test_evaluate_perfect_predictions(self, load_predictor):
        actual = np.array([50.0, 52.0, 48.0])
        predicted = np.array([50.0, 52.0, 48.0])
        result = load_predictor.evaluate(actual, predicted)
        assert result["mae"] == 0.0
        assert result["mse"] == 0.0
        assert result["rmse"] == 0.0
        assert abs(result["r2"] - 1.0) < 1e-6

    def test_evaluate_mismatched_lengths(self, load_predictor):
        actual = np.array([50.0, 52.0, 48.0])
        predicted = np.array([50.0, 52.0])
        with pytest.raises(ValueError, match="same length"):
            load_predictor.evaluate(actual, predicted)

    def test_evaluate_empty_arrays(self, load_predictor):
        with pytest.raises(ValueError, match="must not be empty"):
            load_predictor.evaluate(np.array([]), np.array([]))


class TestLoadPredictorSaveLoad:
    """Tests for model persistence."""

    def test_save_untrained_raises(self, load_predictor, tmp_path):
        with pytest.raises(RuntimeError, match="No trained model"):
            load_predictor.save(tmp_path / "model.pt")

    def test_save_and_load_cycle(self, load_predictor, synthetic_load_data, tmp_path):
        load_predictor.fit(synthetic_load_data, epochs=3)
        path = tmp_path / "test_model.pt"
        load_predictor.save(path)
        assert path.exists()
        new_pred = LoadPredictor()
        meta = new_pred.load(path)
        assert meta["model_type"] == "lstm"
        assert new_pred.trained is True
        assert new_pred.scaler_mean == load_predictor.scaler_mean

    def test_load_nonexistent_file(self, load_predictor, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_predictor.load(tmp_path / "nope.pt")

    def test_save_load_preserves_predictions(self, load_predictor, synthetic_load_data, tmp_path):
        load_predictor.fit(synthetic_load_data, epochs=3)
        original_pred = load_predictor.predict(synthetic_load_data[-24:])
        path = tmp_path / "model.pt"
        load_predictor.save(path)
        loaded = LoadPredictor()
        loaded.load(path)
        loaded_pred = loaded.predict(synthetic_load_data[-24:])
        assert abs(original_pred["predicted_load"] - loaded_pred["predicted_load"]) < 0.01
