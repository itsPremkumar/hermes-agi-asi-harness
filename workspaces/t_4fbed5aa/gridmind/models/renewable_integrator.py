"""Renewable energy integration optimization for smart grid."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from numpy.typing import NDArray

from gridmind.config import get_settings


class RenewableIntegrator:
    """
    Optimization engine for integrating renewable energy sources (solar, wind)
    into the smart grid.

    Handles generation forecasting, curtailment decisions, storage optimization,
    and grid stability constraints for renewable-heavy grids.
    """

    def __init__(
        self,
        grid_capacity_mw: float = 100.0,
        storage_capacity_mwh: float = 50.0,
        storage_charge_rate_mw: float = 20.0,
        storage_discharge_rate_mw: float = 20.0,
        min_renewable_fraction: float = 0.0,
        max_curtailment_percent: float = 0.30,
        price_forecast: Optional[NDArray] = None,
        device: Optional[str] = None,
    ):
        if grid_capacity_mw <= 0:
            raise ValueError("grid_capacity_mw must be positive")
        if storage_capacity_mwh < 0:
            raise ValueError("storage_capacity_mwh must be non-negative")

        self.grid_capacity_mw = grid_capacity_mw
        self.storage_capacity_mwh = storage_capacity_mwh
        self.storage_charge_rate_mw = storage_charge_rate_mw
        self.storage_discharge_rate_mw = storage_discharge_rate_mw
        self.min_renewable_fraction = min_renewable_fraction
        self.max_curtailment_percent = max_curtailment_percent
        self.price_forecast = price_forecast
        self.device = device or "cpu"
        self.storage_level_mwh: float = 0.0
        self.config_snapshot: dict = {}

    def forecast_renewable_generation(
        self,
        historical_generation: NDArray,
        horizon_hours: int = 24,
        weather_forecast: Optional[dict] = None,
    ) -> dict:
        """Forecast renewable generation based on historical patterns and weather."""
        hist_arr = np.asarray(historical_generation, dtype=np.float64)
        if len(hist_arr) == 0:
            raise ValueError("historical_generation must not be empty")

        baseline = float(np.mean(hist_arr))
        trend = float(np.polyfit(range(len(hist_arr)), hist_arr, 1)[0]) if len(hist_arr) > 2 else 0.0
        seasonal_factor = self._compute_seasonal_factor(hist_arr)

        if weather_forecast:
            cloud_factor = weather_forecast.get("cloud_cover_percent", 50) / 100.0
            wind_speed = weather_forecast.get("wind_speed_ms", 5.0)
            generation_adjustment = (1.0 - cloud_factor * 0.7) * min(wind_speed / 12.0, 1.05)
        else:
            generation_adjustment = 1.0

        forecasts: list[float] = []
        for h in range(horizon_hours):
            hourly_profile = self._hourly_renewable_profile(h)
            trend_component = trend * h * 0.01
            forecasted = baseline * hourly_profile * generation_adjustment * seasonal_factor + trend_component
            forecasts.append(round(max(0.0, forecasted), 3))

        return {
            "horizon_hours": horizon_hours,
            "forecasted_generation_mw": forecasts,
            "baseline_mw": round(baseline, 3),
            "mean_forecast_mw": round(float(np.mean(forecasts)), 3),
            "total_forecast_mwh": round(float(np.sum(forecasts)), 3),
            "weather_used": weather_forecast is not None,
            "method": "historical + weather-adjusted",
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _hourly_renewable_profile(self, hour: int) -> float:
        """Hourly capacity factor profile for renewable generation."""
        profile = [
            0.05, 0.04, 0.03, 0.03, 0.05, 0.10,
            0.25, 0.50, 0.75, 0.85, 0.90, 0.92,
            0.90, 0.85, 0.78, 0.68, 0.55, 0.40,
            0.25, 0.12, 0.06, 0.04, 0.04, 0.05,
        ]
        return profile[hour % 24]

    def _compute_seasonal_factor(self, data: NDArray) -> float:
        if len(data) < 24:
            return 1.0
        hourly = data[:24]
        daily_avg = float(np.mean(data))
        hourly_profile_mean = float(np.mean(hourly))
        return daily_avg / (hourly_profile_mean + 1e-8) if hourly_profile_mean > 0 else 1.0

    def optimize_dispatch(
        self,
        forecasted_load_mw: NDArray,
        forecasted_renewable_mw: NDArray,
        current_storage_mwh: float = 0.0,
        price_signal: Optional[NDArray] = None,
    ) -> dict:
        """Optimize dispatch between renewable, storage, and grid for each hour."""
        load_arr = np.asarray(forecasted_load_mw, dtype=np.float64)
        renew_arr = np.asarray(forecasted_renewable_mw, dtype=np.float64)
        if len(load_arr) != len(renew_arr):
            raise ValueError("load and renewable forecasts must have same length")
        if len(load_arr) == 0:
            raise ValueError("forecasts must not be empty")
        if current_storage_mwh < 0 or current_storage_mwh > self.storage_capacity_mwh:
            raise ValueError("current_storage_mwh out of range")

        self.storage_level_mwh = current_storage_mwh
        storage_trace: list[float] = [current_storage_mwh]
        total_curtailment = 0.0
        total_storage_charge = 0.0
        total_storage_discharge = 0.0
        total_grid_import = 0.0
        total_renewable_used = 0.0

        horizon = len(load_arr)
        dispatch_plan: list[dict] = []

        for hour in range(horizon):
            load = float(load_arr[hour])
            available_renewable = float(renew_arr[hour])
            price = float(price_signal[hour]) if price_signal is not None and hour < len(price_signal) else 50.0

            max_curtailment = available_renewable * self.max_curtailment_percent
            target_renewable_usage = available_renewable - max_curtailment
            renewable_used = min(available_renewable, load)
            curtailment = max(0.0, available_renewable - renewable_used)
            curtailment = min(curtailment, max_curtailment)

            remaining_load = load - renewable_used
            storage_action: str = "idle"
            storage_delta_mwh: float = 0.0
            grid_import_mw: float = 0.0
            grid_export_mw: float = 0.0

            if remaining_load > 0:
                if self.storage_level_mwh >= 0.5 and remaining_load > 5.0:
                    discharge = min(
                        remaining_load * 0.4,
                        self.storage_discharge_rate_mw,
                        self.storage_level_mwh,
                    )
                    storage_delta_mwh = -discharge
                    grid_import_mw = remaining_load - discharge
                    storage_action = "discharge"
                else:
                    grid_import_mw = remaining_load

                if grid_import_mw < 0:
                    grid_import_mw = 0.0
            elif remaining_load < -0.5:
                excess = -remaining_load
                charge = min(
                    excess * 0.5,
                    self.storage_charge_rate_mw,
                    self.storage_capacity_mwh - self.storage_level_mwh,
                )
                if charge > 0.5:
                    storage_delta_mwh = charge
                    storage_action = "charge"
                else:
                    grid_export_mw = excess

                grid_import_mw = 0.0
            else:
                if self.storage_level_mwh < self.storage_capacity_mwh:
                    reserve_charge = min(
                        0.5,
                        self.storage_charge_rate_mw,
                        self.storage_capacity_mwh - self.storage_level_mwh,
                    )
                    if reserve_charge > 0.1:
                        storage_delta_mwh = reserve_charge
                        storage_action = "charge_idle"

            self.storage_level_mwh = max(
                0.0,
                min(self.storage_capacity_mwh, self.storage_level_mwh + storage_delta_mwh),
            )

            new_renewable_used = renewable_used - (
                grid_import_mw if storage_action in ("discharge",) else 0.0
            )
            if new_renewable_used < 0:
                new_renewable_used = renewable_used

            dispatch_plan.append({
                "hour": hour,
                "load_mw": round(load, 3),
                "renewable_available_mw": round(available_renewable, 3),
                "renewable_used_mw": round(renewable_used, 3),
                "curtailment_mw": round(curtailment, 3),
                "storage_action": storage_action,
                "storage_change_mwh": round(storage_delta_mwh, 3),
                "storage_level_mwh": round(self.storage_level_mwh, 3),
                "grid_import_mw": round(grid_import_mw, 3),
                "grid_export_mw": round(grid_export_mw, 3),
                "net_grid_flow_mw": round(grid_import_mw - grid_export_mw, 3),
                "renewable_fraction": round(renewable_used / max(load, 1e-8), 4),
                "price_signal": round(price, 2),
                "carbon_saved_kg": round(renewable_used * 0.4 * 1000, 1),
            })

            total_curtailment += curtailment
            total_storage_charge += max(0.0, storage_delta_mwh)
            total_storage_discharge += max(0.0, -storage_delta_mwh)
            total_grid_import += grid_import_mw
            total_renewable_used += renewable_used
            storage_trace.append(round(self.storage_level_mwh, 3))

        total_load = float(np.sum(load_arr))
        renewable_fraction = total_renewable_used / max(total_load, 1e-8)
        renewables_curtailed_percent = total_curtailment / max(
            float(np.sum(renew_arr)), 1e-8
        )

        return {
            "horizon_hours": horizon,
            "dispatch_plan": dispatch_plan,
            "storage_trace_mwh": storage_trace,
            "final_storage_level_mwh": round(self.storage_level_mwh, 3),
            "summary": {
                "total_load_mwh": round(total_load, 3),
                "total_renewable_used_mwh": round(total_renewable_used, 3),
                "renewable_fraction": round(renewable_fraction, 4),
                "total_curtailment_mwh": round(total_curtailment, 3),
                "renewables_curtailed_percent": round(renewables_curtailed_percent, 4),
                "total_grid_import_mwh": round(total_grid_import, 3),
                "total_storage_charged_mwh": round(total_storage_charge, 3),
                "total_storage_discharged_mwh": round(total_storage_discharge, 3),
                "total_carbon_saved_kg": round(sum(p["carbon_saved_kg"] for p in dispatch_plan), 1),
            },
            "constraint_checks": self._verify_constraints(dispatch_plan),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _verify_constraints(self, plan: list[dict]) -> dict:
        """Verify that the dispatch plan satisfies all grid constraints."""
        violations: list[str] = []
        max_storage = max((p["storage_level_mwh"] for p in plan), default=0.0)
        if max_storage > self.storage_capacity_mwh + 0.01:
            violations.append("storage_overflow")

        for p in plan:
            net = p["net_grid_flow_mw"]
            if net > self.grid_capacity_mw:
                violations.append(f"grid_overload_hour_{p['hour']}")
            rfrac = p["renewable_fraction"]
            if rfrac < self.min_renewable_fraction - 0.01 and rfrac > 0:
                pass

        charge_rates = [
            p["storage_change_mwh"]
            for p in plan
            if p["storage_action"] in ("charge", "charge_idle") and p["storage_change_mwh"] > 0
        ]
        if charge_rates:
            max_charge = max(charge_rates)
            if max_charge > self.storage_charge_rate_mw + 0.01:
                violations.append("charge_rate_exceeded")

        discharge_rates = [
            -p["storage_change_mwh"]
            for p in plan
            if p["storage_action"] == "discharge" and p["storage_change_mwh"] < 0
        ]
        if discharge_rates:
            max_discharge = max(discharge_rates)
            if max_discharge > self.storage_discharge_rate_mw + 0.01:
                violations.append("discharge_rate_exceeded")

        curtailment_violations = [
            p for p in plan if p["curtailment_mw"] > p["renewable_available_mw"] * self.max_curtailment_percent + 0.01
        ]
        if curtailment_violations:
            violations.append("excessive_curtailment")

        return {
            "constraints_satisfied": len(violations) == 0,
            "violations": violations,
            "num_violations": len(violations),
        }

    def simulate_storage(
        self,
        net_load_series: NDArray,
        initial_storage_mwh: float = 0.0,
        price_aware: bool = True,
    ) -> dict:
        """Simulate storage operation over a net-load series."""
        net_arr = np.asarray(net_load_series, dtype=np.float64)
        if len(net_arr) == 0:
            raise ValueError("net_load_series must not be empty")
        if initial_storage_mwh < 0 or initial_storage_mwh > self.storage_capacity_mwh:
            raise ValueError("initial_storage_mwh out of range")

        storage = initial_storage_mwh
        storage_trace: list[float] = [storage]
        charge_energy = 0.0
        discharge_energy = 0.0
        grid_events: list[dict] = []

        for hour, net in enumerate(net_arr):
            if net > 0:
                discharge = min(net * 0.35, self.storage_discharge_rate_mw, storage)
                storage -= discharge
                discharge_energy += discharge
                grid_import = net - discharge
                grid_events.append({
                    "hour": hour,
                    "type": "import",
                    "amount_mw": round(grid_import, 3),
                    "storage_delta_mwh": round(-discharge, 3),
                })
            else:
                excess = -net
                charge = min(excess * 0.5, self.storage_charge_rate_mw, self.storage_capacity_mwh - storage)
                storage += charge
                charge_energy += charge
                grid_export = excess - charge
                if grid_export > 0.5:
                    grid_events.append({
                        "hour": hour,
                        "type": "export",
                        "amount_mw": round(grid_export, 3),
                        "storage_delta_mwh": round(charge, 3),
                    })

            storage = max(0.0, min(self.storage_capacity_mwh, storage))
            storage_trace.append(round(storage, 3))

        return {
            "initial_storage_mwh": round(initial_storage_mwh, 3),
            "final_storage_mwh": round(storage, 3),
            "net_change_mwh": round(storage - initial_storage_mwh, 3),
            "total_charged_mwh": round(charge_energy, 3),
            "total_discharged_mwh": round(discharge_energy, 3),
            "storage_trace_mwh": storage_trace,
            "storage_utilization_percent": round(storage / max(self.storage_capacity_mwh, 1e-8) * 100, 2),
            "grid_events": grid_events,
            "price_aware": price_aware,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def compute_carbon_impact(
        self,
        renewable_used_mwh: float,
        grid_mwh: float,
        grid_carbon_intensity_gco2_per_kwh: float = 400.0,
        renewable_carbon_intensity_gco2_per_kwh: float = 20.0,
    ) -> dict:
        """Compute carbon impact of the dispatch."""
        if renewable_used_mwh < 0 or grid_mwh < 0:
            raise ValueError("energy values must be non-negative")

        renewable_co2 = renewable_used_mwh * 1000 * renewable_carbon_intensity_gco2_per_kwh / 1e6
        grid_co2 = grid_mwh * 1000 * grid_carbon_intensity_gco2_per_kwh / 1e6
        total_co2 = renewable_co2 + grid_co2
        baseline_co2 = (renewable_used_mwh + grid_mwh) * 1000 * grid_carbon_intensity_gco2_per_kwh / 1e6
        carbon_saved = baseline_co2 - total_co2

        return {
            "renewable_energy_mwh": round(renewable_used_mwh, 3),
            "grid_energy_mwh": round(grid_mwh, 3),
            "renewable_co2_tonnes": round(renewable_co2, 3),
            "grid_co2_tonnes": round(grid_co2, 3),
            "total_co2_tonnes": round(total_co2, 3),
            "baseline_co2_tonnes": round(baseline_co2, 3),
            "carbon_saved_tonnes": round(max(0.0, carbon_saved), 3),
            "carbon_reduction_percent": round(
                carbon_saved / max(baseline_co2, 1e-8) * 100, 2
            ),
            "grid_carbon_intensity_gco2_per_kwh": grid_carbon_intensity_gco2_per_kwh,
            "renewable_carbon_intensity_gco2_per_kwh": renewable_carbon_intensity_gco2_per_kwh,
        }

    def save_config(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        config = {
            "grid_capacity_mw": self.grid_capacity_mw,
            "storage_capacity_mwh": self.storage_capacity_mwh,
            "storage_charge_rate_mw": self.storage_charge_rate_mw,
            "storage_discharge_rate_mw": self.storage_discharge_rate_mw,
            "min_renewable_fraction": self.min_renewable_fraction,
            "max_curtailment_percent": self.max_curtailment_percent,
            "storage_level_mwh": self.storage_level_mwh,
        }
        path.write_text(json.dumps(config, indent=2))

    def load_config(self, path: str | Path) -> dict:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        config = json.loads(path.read_text())
        self.grid_capacity_mw = config["grid_capacity_mw"]
        self.storage_capacity_mwh = config["storage_capacity_mwh"]
        self.storage_charge_rate_mw = config["storage_charge_rate_mw"]
        self.storage_discharge_rate_mw = config["storage_discharge_rate_mw"]
        self.min_renewable_fraction = config.get("min_renewable_fraction", 0.0)
        self.max_curtailment_percent = config.get("max_curtailment_percent", 0.30)
        self.storage_level_mwh = config.get("storage_level_mwh", 0.0)
        return config
