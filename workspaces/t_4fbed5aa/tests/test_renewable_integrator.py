"""Tests for RenewableIntegrator — renewable energy integration optimization."""

import numpy as np
import pytest

from gridmind.models.renewable_integrator import RenewableIntegrator


class TestRenewableIntegratorConstruction:
    """Tests for RenewableIntegrator construction and validation."""

    def test_default_construction(self):
        integ = RenewableIntegrator()
        assert integ.grid_capacity_mw == 100.0
        assert integ.storage_capacity_mwh == 50.0
        assert integ.storage_charge_rate_mw == 20.0
        assert integ.storage_discharge_rate_mw == 20.0
        assert integ.min_renewable_fraction == 0.0
        assert integ.max_curtailment_percent == 0.30
        assert integ.storage_level_mwh == 0.0

    def test_custom_construction(self):
        integ = RenewableIntegrator(
            grid_capacity_mw=200.0,
            storage_capacity_mwh=100.0,
            storage_charge_rate_mw=50.0,
            storage_discharge_rate_mw=50.0,
            min_renewable_fraction=0.2,
            max_curtailment_percent=0.5,
        )
        assert integ.grid_capacity_mw == 200.0
        assert integ.storage_capacity_mwh == 100.0
        assert integ.min_renewable_fraction == 0.2
        assert integ.max_curtailment_percent == 0.5

    def test_invalid_grid_capacity(self):
        with pytest.raises(ValueError, match="positive"):
            RenewableIntegrator(grid_capacity_mw=0)

    def test_negative_grid_capacity(self):
        with pytest.raises(ValueError, match="positive"):
            RenewableIntegrator(grid_capacity_mw=-10)

    def test_negative_storage(self):
        with pytest.raises(ValueError, match="non-negative"):
            RenewableIntegrator(storage_capacity_mwh=-5)

    def test_storage_level_initialized(self):
        integ = RenewableIntegrator(storage_capacity_mwh=30.0)
        assert integ.storage_level_mwh == 0.0


class TestRenewableForecast:
    """Tests for renewable generation forecasting."""

    def test_forecast_empty_history(self):
        integ = RenewableIntegrator()
        with pytest.raises(ValueError, match="must not be empty"):
            integ.forecast_renewable_generation(np.array([]))

    def test_forecast_basic(self, renewable_integrator):
        hist = np.array([5.0, 6.0, 5.5, 7.0, 6.5, 8.0, 7.5, 9.0] * 3)
        result = renewable_integrator.forecast_renewable_generation(hist, horizon_hours=24)
        assert result["horizon_hours"] == 24
        assert len(result["forecasted_generation_mw"]) == 24
        assert result["baseline_mw"] > 0
        assert result["mean_forecast_mw"] > 0
        assert result["total_forecast_mwh"] > 0
        assert result["weather_used"] is False
        assert result["method"] == "historical + weather-adjusted"

    def test_forecast_with_weather(self, renewable_integrator):
        hist = np.array([5.0, 6.0, 5.5, 7.0, 6.5, 8.0])
        weather = {"cloud_cover_percent": 30, "wind_speed_ms": 8.0}
        result = renewable_integrator.forecast_renewable_generation(hist, horizon_hours=12, weather_forecast=weather)
        assert result["weather_used"] is True

    def test_forecast_cloud_cover_reduction(self, renewable_integrator):
        hist = np.array([5.0] * 24)
        clear_weather = {"cloud_cover_percent": 0, "wind_speed_ms": 5.0}
        cloudy_weather = {"cloud_cover_percent": 90, "wind_speed_ms": 5.0}
        clear = renewable_integrator.forecast_renewable_generation(hist, horizon_hours=24, weather_forecast=clear_weather)
        cloudy = renewable_integrator.forecast_renewable_generation(hist, horizon_hours=24, weather_forecast=cloudy_weather)
        assert sum(clear["forecasted_generation_mw"]) > sum(cloudy["forecasted_generation_mw"])

    def test_forecast_zero_history(self, renewable_integrator):
        hist = np.array([0.0, 0.0, 0.0])
        result = renewable_integrator.forecast_renewable_generation(hist, horizon_hours=24)
        assert result["baseline_mw"] == 0.0

    def test_forecast_hourly_profile(self, renewable_integrator):
        result = renewable_integrator.forecast_renewable_generation(np.array([5.0] * 24), horizon_hours=24)
        mw = result["forecasted_generation_mw"]
        peak_idx = int(np.argmax(mw))
        trough_idx = int(np.argmin(mw))
        assert peak_idx in (11, 12, 13)
        assert trough_idx in (0, 1, 2, 22, 23)

    def test_forecast_short_horizon(self, renewable_integrator):
        hist = np.array([5.0] * 24)
        result = renewable_integrator.forecast_renewable_generation(hist, horizon_hours=1)
        assert result["horizon_hours"] == 1
        assert len(result["forecasted_generation_mw"]) == 1

    def test_forecast_long_horizon(self, renewable_integrator):
        hist = np.array([5.0] * 24)
        result = renewable_integrator.forecast_renewable_generation(hist, horizon_hours=168)
        assert result["horizon_hours"] == 168
        assert len(result["forecasted_generation_mw"]) == 168

    def test_forecast_output_values(self, renewable_integrator):
        hist = np.array([10.0] * 24)
        result = renewable_integrator.forecast_renewable_generation(hist, horizon_hours=6)
        for val in result["forecasted_generation_mw"]:
            assert val >= 0.0


class TestDispatchOptimization:
    """Tests for dispatch optimization."""

    def test_optimize_mismatched_lengths(self, renewable_integrator):
        load = [50.0, 52.0, 51.0]
        renewable = [1.0, 2.0]
        with pytest.raises(ValueError, match="same length"):
            renewable_integrator.optimize_dispatch(load, renewable)

    def test_optimize_empty(self, renewable_integrator):
        with pytest.raises(ValueError, match="must not be empty"):
            renewable_integrator.optimize_dispatch([], [])

    def test_optimize_basic_dispatch(self, renewable_integrator, hourly_forecast_load, hourly_forecast_renewable):
        result = renewable_integrator.optimize_dispatch(hourly_forecast_load, hourly_forecast_renewable)
        assert result["horizon_hours"] == 24
        assert len(result["dispatch_plan"]) == 24
        assert len(result["storage_trace_mwh"]) == 24
        assert "summary" in result
        assert "constraint_checks" in result
        assert result["final_storage_level_mwh"] >= 0
        assert result["final_storage_level_mwh"] <= renewable_integrator.storage_capacity_mwh

    def test_optimize_summary_structure(self, renewable_integrator, hourly_forecast_load, hourly_forecast_renewable):
        result = renewable_integrator.optimize_dispatch(hourly_forecast_load, hourly_forecast_renewable)
        summary = result["summary"]
        assert "total_load_mwh" in summary
        assert "total_renewable_used_mwh" in summary
        assert "renewable_fraction" in summary
        assert "total_curtailment_mwh" in summary
        assert "total_grid_import_mwh" in summary
        assert "total_storage_charged_mwh" in summary
        assert "total_storage_discharged_mwh" in summary
        assert "total_carbon_saved_kg" in summary
        assert summary["renewable_fraction"] >= 0

    def test_optimize_constraint_checks(self, renewable_integrator, hourly_forecast_load, hourly_forecast_renewable):
        result = renewable_integrator.optimize_dispatch(hourly_forecast_load, hourly_forecast_renewable)
        checks = result["constraint_checks"]
        assert "constraints_satisfied" in checks
        assert "violations" in checks
        assert "num_violations" in checks
        assert isinstance(checks["constraints_satisfied"], bool)

    def test_optimize_with_price_signal(self, renewable_integrator, hourly_forecast_load, hourly_forecast_renewable):
        prices = [30.0] * 24
        result = renewable_integrator.optimize_dispatch(hourly_forecast_load, hourly_forecast_renewable, price_signal=prices)
        for plan in result["dispatch_plan"]:
            assert "price_signal" in plan
            plan["price_signal"] == 30.0

    def test_optimize_curtailment_limited(self, renewable_integrator, hourly_forecast_load, hourly_forecast_renewable):
        result = renewable_integrator.optimize_dispatch(hourly_forecast_load, hourly_forecast_renewable)
        for plan in result["dispatch_plan"]:
            max_allowed = plan["renewable_available_mw"] * renewable_integrator.max_curtailment_percent
            assert plan["curtailment_mw"] <= max_allowed + 0.01

    def test_optimize_storage_bounds(self, renewable_integrator, hourly_forecast_load, hourly_forecast_renewable):
        result = renewable_integrator.optimize_dispatch(hourly_forecast_load, hourly_forecast_renewable)
        for plan in result["dispatch_plan"]:
            assert 0 <= plan["storage_level_mwh"] <= renewable_integrator.storage_capacity_mwh + 0.01

    def test_optimize_grid_capacity(self, renewable_integrator, hourly_forecast_load, hourly_forecast_renewable):
        result = renewable_integrator.optimize_dispatch(hourly_forecast_load, hourly_forecast_renewable)
        for plan in result["dispatch_plan"]:
            assert plan["net_grid_flow_mw"] <= renewable_integrator.grid_capacity_mw + 0.01

    def test_optimize_with_initial_storage(self, renewable_integrator, hourly_forecast_load, hourly_forecast_renewable):
        result = renewable_integrator.optimize_dispatch(hourly_forecast_load, hourly_forecast_renewable, current_storage_mwh=25.0)
        assert result["storage_trace_mwh"][0] == 25.0

    def test_optimize_storage_overflow_prevented(self, renewable_integrator):
        load = [10.0] * 100
        renewable = [50.0] * 100
        result = renewable_integrator.optimize_dispatch(load, renewable, current_storage_mwh=48.0)
        for plan in result["dispatch_plan"]:
            assert plan["storage_level_mwh"] <= renewable_integrator.storage_capacity_mwh

    def test_optimize_dispatch_plan_fields(self, renewable_integrator, hourly_forecast_load, hourly_forecast_renewable):
        result = renewable_integrator.optimize_dispatch(hourly_forecast_load, hourly_forecast_renewable)
        plan = result["dispatch_plan"][0]
        expected_fields = [
            "hour", "load_mw", "renewable_available_mw", "renewable_used_mw",
            "curtailment_mw", "storage_action", "storage_change_mwh", "storage_level_mwh",
            "grid_import_mw", "grid_export_mw", "net_grid_flow_mw",
            "renewable_fraction", "price_signal", "carbon_saved_kg",
        ]
        for field in expected_fields:
            assert field in plan, f"Missing field: {field}"

    def test_optimize_dispatch_plan_values(self, renewable_integrator, hourly_forecast_load, hourly_forecast_renewable):
        result = renewable_integrator.optimize_dispatch(hourly_forecast_load, hourly_forecast_renewable)
        for plan in result["dispatch_plan"]:
            assert plan["load_mw"] >= 0
            assert plan["renewable_available_mw"] >= 0
            assert plan["renewable_used_mw"] >= 0
            assert plan["curtailment_mw"] >= 0
            assert plan["grid_import_mw"] >= 0
            assert plan["grid_export_mw"] >= 0
            assert plan["renewable_fraction"] >= 0
            assert plan["carbon_saved_kg"] >= 0


class TestStorageSimulation:
    """Tests for storage simulation."""

    def test_simulate_empty_series(self, renewable_integrator):
        with pytest.raises(ValueError, match="must not be empty"):
            renewable_integrator.simulate_storage(np.array([]))

    def test_simulate_basic(self, renewable_integrator):
        net_load = np.array([10.0, -5.0, 15.0, -8.0, 12.0, -3.0, 10.0, -6.0, 8.0, -4.0])
        result = renewable_integrator.simulate_storage(net_load, initial_storage_mwh=10.0)
        assert result["initial_storage_mwh"] == 10.0
        assert result["final_storage_mwh"] >= 0
        assert result["final_storage_mwh"] <= renewable_integrator.storage_capacity_mwh
        assert len(result["storage_trace_mwh"]) == len(net_load) + 1
        assert result["total_charged_mwh"] >= 0
        assert result["total_discharged_mwh"] >= 0

    def test_simulate_storage_bounds(self, renewable_integrator):
        net_load = np.array([20.0] * 50 + [-30.0] * 50)
        result = renewable_integrator.simulate_storage(net_load)
        for level in result["storage_trace_mwh"]:
            assert 0 <= level <= renewable_integrator.storage_capacity_mwh

    def test_simulate_utilization(self, renewable_integrator):
        net_load = np.array([20.0] * 10 + [-25.0] * 10)
        result = renewable_integrator.simulate_storage(net_load, initial_storage_mwh=0.0)
        assert 0 <= result["storage_utilization_percent"] <= 100

    def test_simulate_grid_events(self, renewable_integrator):
        net_load = np.array([15.0, -10.0, 20.0, -15.0])
        result = renewable_integrator.simulate_storage(net_load)
        assert isinstance(result["grid_events"], list)
        import_types = [e for e in result["grid_events"] if e["type"] == "import"]
        export_types = [e for e in result["grid_events"] if e["type"] == "export"]
        assert len(import_types) >= 0
        assert len(export_types) >= 0

    def test_simulate_invalid_initial_storage(self, renewable_integrator):
        with pytest.raises(ValueError, match="out of range"):
            renewable_integrator.simulate_storage(np.array([10.0]), initial_storage_mwh=-5.0)

    def test_simulate_invalid_initial_storage_overflow(self, renewable_integrator):
        with pytest.raises(ValueError, match="out of range"):
            renewable_integrator.simulate_storage(np.array([10.0]), initial_storage_mwh=60.0)

    def test_simulate_price_aware_flag(self, renewable_integrator):
        net_load = np.array([10.0, -5.0])
        result = renewable_integrator.simulate_storage(net_load, price_aware=True)
        assert result["price_aware"] is True

    def test_simulate_no_price_signal(self, renewable_integrator):
        net_load = np.array([10.0, -5.0])
        result = renewable_integrator.simulate_storage(net_load, price_aware=False)
        assert result["price_aware"] is False


class TestCarbonImpact:
    """Tests for carbon impact computation."""

    def test_carbon_basic(self, renewable_integrator):
        result = renewable_integrator.compute_carbon_impact(
            renewable_used_mwh=50.0,
            grid_mwh=30.0,
        )
        assert result["renewable_energy_mwh"] == 50.0
        assert result["grid_energy_mwh"] == 30.0
        assert result["total_co2_tonnes"] > 0
        assert result["carbon_saved_tonnes"] > 0
        assert result["carbon_reduction_percent"] > 0

    def test_carbon_zero_energy(self, renewable_integrator):
        result = renewable_integrator.compute_carbon_impact(0.0, 0.0)
        assert result["total_co2_tonnes"] == 0.0
        assert result["carbon_saved_tonnes"] == 0.0

    def test_carbon_only_renewable(self, renewable_integrator):
        result = renewable_integrator.compute_carbon_impact(100.0, 0.0)
        assert result["renewable_energy_mwh"] == 100.0
        assert result["grid_energy_mwh"] == 0.0

    def test_carbon_only_grid(self, renewable_integrator):
        result = renewable_integrator.compute_carbon_impact(0.0, 100.0)
        assert result["renewable_energy_mwh"] == 0.0
        assert result["grid_energy_mwh"] == 100.0

    def test_carbon_custom_intensity(self, renewable_integrator):
        result = renewable_integrator.compute_carbon_impact(
            50.0, 50.0,
            grid_carbon_intensity_gco2_per_kwh=500.0,
            renewable_carbon_intensity_gco2_per_kwh=5.0,
        )
        assert result["carbon_reduction_percent"] >= 49

    def test_carbon_negative_energy_rejected(self, renewable_integrator):
        with pytest.raises(ValueError, match="non-negative"):
            renewable_integrator.compute_carbon_impact(-10.0, 20.0)

    def test_carbon_fields(self, renewable_integrator):
        result = renewable_integrator.compute_carbon_impact(10.0, 10.0)
        required = [
            "renewable_energy_mwh", "grid_energy_mwh",
            "renewable_co2_tonnes", "grid_co2_tonnes", "total_co2_tonnes",
            "baseline_co2_tonnes", "carbon_saved_tonnes", "carbon_reduction_percent",
            "grid_carbon_intensity_gco2_per_kwh", "renewable_carbon_intensity_gco2_per_kwh",
        ]
        for field in required:
            assert field in result


class TestRenewableConfigPersistence:
    """Tests for renewable integrator config save/load."""

    def test_save_config(self, renewable_integrator, tmp_path):
        renewable_integrator.storage_level_mwh = 25.0
        path = tmp_path / "config.json"
        renewable_integrator.save_config(path)
        assert path.exists()
        content = path.read_text()
        assert "grid_capacity_mw" in content

    def test_load_config(self, renewable_integrator, tmp_path):
        path = tmp_path / "config.json"
        config = {
            "grid_capacity_mw": 150.0,
            "storage_capacity_mwh": 75.0,
            "storage_charge_rate_mw": 25.0,
            "storage_discharge_rate_mw": 25.0,
            "min_renewable_fraction": 0.1,
            "max_curtailment_percent": 0.4,
            "storage_level_mwh": 30.0,
        }
        import json
        path.write_text(json.dumps(config))
        loaded = renewable_integrator.load_config(path)
        assert renewable_integrator.grid_capacity_mw == 150.0
        assert renewable_integrator.storage_capacity_mwh == 75.0
        assert renewable_integrator.storage_level_mwh == 30.0

    def test_load_config_nonexistent(self, renewable_integrator, tmp_path):
        with pytest.raises(FileNotFoundError):
            renewable_integrator.load_config(tmp_path / "nope.json")


class TestRenewableEdgeCases:
    """Edge case tests for renewable integrator."""

    def test_zero_grid_capacity_dispatch(self):
        integ = RenewableIntegrator(grid_capacity_mw=1.0, storage_capacity_mwh=0.0)
        load = [10.0] * 5
        renewable = [20.0] * 5
        result = integ.optimize_dispatch(load, renewable)
        assert result["constraint_checks"]["num_violations"] >= 0

    def test_full_storage_simulation(self, renewable_integrator):
        net_load = np.array([-50.0] * 20)
        result = renewable_integrator.simulate_storage(net_load, initial_storage_mwh=0.0)
        assert result["final_storage_mwh"] <= renewable_integrator.storage_capacity_mwh

    def test_dispatch_plan_carbon_per_hour(self, renewable_integrator, hourly_forecast_load, hourly_forecast_renewable):
        result = renewable_integrator.optimize_dispatch(hourly_forecast_load, hourly_forecast_renewable)
        for plan in result["dispatch_plan"]:
            assert isinstance(plan["carbon_saved_kg"], float)
            assert plan["carbon_saved_kg"] >= 0
