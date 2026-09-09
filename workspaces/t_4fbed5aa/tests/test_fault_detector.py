"""Tests for FaultDetector — anomaly detection and fault identification."""

import numpy as np
import pytest

from gridmind.models.fault_detector import FaultDetector, FaultType


class TestFaultType:
    """Tests for FaultType enumeration."""

    def test_fault_type_values(self):
        assert FaultType.NONE.value == "none"
        assert FaultType.OVER_VOLTAGE.value == "over_voltage"
        assert FaultType.UNDER_VOLTAGE.value == "under_voltage"
        assert FaultType.OVER_CURRENT.value == "over_current"
        assert FaultType.UNDER_CURRENT.value == "under_current"
        assert FaultType.FREQUENCY_DRIFT.value == "frequency_drift"
        assert FaultType.PHASE_IMBALANCE.value == "phase_imbalance"
        assert FaultType.HARMONIC_DISTORTION.value == "harmonic_distortion"
        assert FaultType.TEMPERATURE_ANomaly.value == "temperature_anomaly"
        assert FaultType.COMBINED.value == "combined"


class TestFaultDetectorConstruction:
    """Tests for FaultDetector construction."""

    def test_default_construction(self):
        det = FaultDetector()
        assert det.sensor_dims == 10
        assert det.latent_dim == 16
        assert det.encoder_hidden == (64, 32)
        assert det.learning_rate == 1e-3
        assert det.epochs == 50
        assert det.batch_size == 64
        assert det.anomaly_threshold_percentile == 95.0
        assert det.trained is False
        assert det.model is None
        assert det.threshold == 0.0

    def test_custom_construction(self):
        det = FaultDetector(
            sensor_dims=5,
            latent_dim=8,
            encoder_hidden=(32, 16),
            learning_rate=5e-4,
            epochs=20,
            batch_size=128,
            anomaly_threshold_percentile=99.0,
        )
        assert det.sensor_dims == 5
        assert det.latent_dim == 8
        assert det.anomaly_threshold_percentile == 99.0

    def test_device_cpu(self):
        det = FaultDetector(device="cpu")
        assert det.device == "cpu"


class TestFaultDetectorTraining:
    """Tests for FaultDetector training."""

    def test_train_wrong_dimensions(self, fault_detector):
        data = np.random.randn(200, 5)
        with pytest.raises(ValueError, match="Expected 8 sensor dims"):
            fault_detector.fit(data)

    def test_train_1d_data_rejected(self, fault_detector):
        data = np.random.randn(200)
        with pytest.raises(ValueError, match="must be 2D"):
            fault_detector.fit(data)

    def test_train_too_few_samples(self, fault_detector):
        data = np.random.randn(50, 8)
        with pytest.raises(ValueError, match="at least 100 samples"):
            fault_detector.fit(data)

    def test_train_success(self, fault_detector, synthetic_sensor_data):
        result = fault_detector.fit(synthetic_sensor_data, epochs=3)
        assert fault_detector.trained is True
        assert result["model_type"] == "autoencoder"
        assert "threshold" in result
        assert result["trained"] is True
        assert result["sensor_dims"] == 8

    def test_train_sets_threshold(self, fault_detector, synthetic_sensor_data):
        fault_detector.fit(synthetic_sensor_data, epochs=3)
        assert fault_detector.threshold > 0

    def test_train_history(self, fault_detector, synthetic_sensor_data):
        fault_detector.fit(synthetic_sensor_data, epochs=5)
        assert len(fault_detector.reconstruction_errors) > 0


class TestFaultDetectorSingleDetection:
    """Tests for single reading fault detection."""

    def test_detect_untrained_default(self, fault_detector):
        fault_detector.sensor_dims = 8
        reading = np.array([230.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0])
        assert "anomaly_score" in result
        assert "timestamp" in result
        assert "detected_faults" in result
        assert "severity" in result
        assert result["sensor_dims"] == 10

    def test_detect_normal_reading(self, fault_detector, synthetic_sensor_data):
        fault_detector.fit(synthetic_sensor_data, epochs=3)
        reading = synthetic_sensor_data[0].copy()
        result = fault_detector.detect(reading)
        assert isinstance(result["anomaly_score"], float)
        assert isinstance(result["is_anomaly"], bool)
        assert isinstance(result["detected_faults"], list)

    def test_detect_over_voltage(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        reading = np.array([270.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0])
        result = det.detect(reading, rules=True)
        assert FaultType.OVER_VOLTAGE.value in result["detected_faults"]

    def test_detect_under_voltage(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        reading = np.array([200.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0])
        result = det.detect(reading, rules=True)
        assert FaultType.UNDER_VOLTAGE.value in result["detected_faults"]

    def test_detect_over_current(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        reading = np.array([230.0, 130.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0])
        result = det.detect(reading, rules=True)
        assert FaultType.OVER_CURRENT.value in result["detected_faults"]

    def test_detect_frequency_drift(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        reading = np.array([230.0, 50.0, 52.0, 225.0, 226.0, 227.0, 2.0, 45.0])
        result = det.detect(reading, rules=True)
        assert FaultType.FREQUENCY_DRIFT.value in result["detected_faults"]

    def test_detect_phase_imbalance(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        reading = np.array([230.0, 50.0, 50.0, 225.0, 260.0, 260.0, 2.0, 45.0])
        result = det.detect(reading, rules=True)
        assert FaultType.PHASE_IMBALANCE.value in result["detected_faults"]

    def test_detect_harmonic_distortion(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        reading = np.array([230.0, 50.0, 50.0, 225.0, 226.0, 227.0, 8.0, 45.0])
        result = det.detect(reading, rules=True)
        assert FaultType.HARMONIC_DISTORTION.value in result["detected_faults"]

    def test_detect_temperature_anomaly(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        reading = np.array([230.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 95.0])
        result = det.detect(reading, rules=True)
        assert FaultType.TEMPERATURE_ANomaly.value in result["detected_faults"]

    def test_detect_combined_faults(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        reading = np.array([270.0, 130.0, 52.0, 225.0, 260.0, 260.0, 8.0, 95.0])
        result = det.detect(reading, rules=True)
        assert FaultType.COMBINED.value in result["detected_faults"]

    def test_detect_severity_levels(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        normal = np.array([230.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0])
        r = det.detect(normal, rules=False)
        assert r["severity"] == "normal"

    def test_detect_rules_disabled(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        reading = np.array([270.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0])
        result = det.detect(reading, rules=False)
        assert FaultType.OVER_VOLTAGE.value not in result["detected_faults"]

    def test_detect_dimension_mismatch(self, fault_detector):
        fault_detector.sensor_dims = 8
        reading = np.array([230.0, 50.0, 50.0])
        with pytest.raises(ValueError, match="Expected 8 sensor dims"):
            fault_detector.detect(reading)

    def test_detect_1d_reading_reshaped(self, fault_detector, synthetic_sensor_data):
        fault_detector.fit(synthetic_sensor_data, epochs=3)
        reading = synthetic_sensor_data[0]
        result = fault_detector.detect(reading)
        assert isinstance(result, dict)
        assert "anomaly_score" in result


class TestFaultDetectorBatchDetection:
    """Tests for batch fault detection."""

    def test_batch_detect_empty_raises(self, fault_detector):
        with pytest.raises(IndexError):
            fault_detector.detect_batch(np.array([]))

    def test_batch_detect_normal(self, fault_detector, synthetic_sensor_data):
        fault_detector.fit(synthetic_sensor_data, epochs=3)
        batch = synthetic_sensor_data[:10]
        result = fault_detector.detect_batch(batch)
        assert result["total_readings"] == 10
        assert result["anomalies_detected"] >= 0
        assert result["critical_count"] >= 0
        assert result["anomaly_rate"] >= 0.0
        assert len(result["results"]) == 10

    def test_batch_detect_all_normal(self, fault_detector, synthetic_sensor_data):
        fault_detector.fit(synthetic_sensor_data, epochs=3)
        batch = synthetic_sensor_data[:5]
        result = fault_detector.detect_batch(batch)
        for res in result["results"]:
            assert "detected_faults" in res
            assert "severity" in res

    def test_batch_detect_mixed(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        readings = np.array([
            [230.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0],
            [270.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0],
            [230.0, 130.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0],
        ])
        result = det.detect_batch(readings)
        assert result["total_readings"] == 3
        assert result["anomalies_detected"] >= 0


class TestFaultDetectorPersistence:
    """Tests for fault detector save/load."""

    def test_save_untrained_raises(self, fault_detector, tmp_path):
        with pytest.raises(RuntimeError, match="No trained model"):
            fault_detector.save(tmp_path / "fault_model.pt")

    def test_save_and_load(self, fault_detector, synthetic_sensor_data, tmp_path):
        fault_detector.fit(synthetic_sensor_data, epochs=3)
        path = tmp_path / "fault.pt"
        fault_detector.save(path)
        assert path.exists()
        new_det = FaultDetector()
        meta = new_det.load(path)
        assert meta["sensor_dims"] == 8
        assert new_det.trained is True
        assert new_det.threshold == fault_detector.threshold


class TestFaultDetectorEdgeCases:
    """Edge case tests for fault detector."""

    def test_many_faults_critical_severity(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        reading = np.array([270.0, 130.0, 55.0, 225.0, 260.0, 260.0, 10.0, 100.0])
        result = det.detect(reading, rules=True)
        assert result["severity"] == "critical"

    def test_single_fault_warning_severity(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        reading = np.array([270.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0])
        result = det.detect(reading, rules=True)
        assert result["severity"] == "warning"

    def test_no_faults_normal_severity(self, fault_detector):
        det = FaultDetector(sensor_dims=8)
        reading = np.array([230.0, 50.0, 50.0, 225.0, 226.0, 227.0, 2.0, 45.0])
        result = det.detect(reading, rules=True)
        assert result["severity"] == "normal"

    def test_anomaly_score_structure(self, fault_detector, synthetic_sensor_data):
        fault_detector.fit(synthetic_sensor_data, epochs=3)
        reading = synthetic_sensor_data[0]
        result = fault_detector.detect(reading)
        assert "anomaly_score" in result
        assert "threshold" in result
        assert "is_anomaly" in result
        assert isinstance(result["anomaly_score"], float)
        assert isinstance(result["threshold"], float)
        assert isinstance(result["is_anomaly"], bool)
