from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from agents.optimization_agent import OptimizationAgent


agent = OptimizationAgent()


def run_case(
    name: str,
    telemetry: dict,
    action: str,
    predicted_demand_kw: float,
) -> None:

    print("\n" + "=" * 80)
    print(f"SCENARIO: {name}")
    print("=" * 80)

    decision = SimpleNamespace(
        action=action,
    )

    forecast = SimpleNamespace(
        predicted_demand_kw=predicted_demand_kw,
    )

    result = agent.optimize(
        telemetry=telemetry,
        supervisor_decision=decision,
        forecast_result=forecast,
    )

    for key, value in result.to_dict().items():
        print(f"{key:32}: {value}")


base = {
    "demand_kw": 50.0,
    "solar_generation_kw": 8.0,
    "battery_soc_percent": 72.0,
    "grid_price_inr_per_kwh": 6.5,
    "grid_carbon_intensity_g_per_kwh": 520.0,
}


run_case(
    name="Normal Hold",
    telemetry=base,
    action="MAINTAIN_CURRENT_OPERATION",
    predicted_demand_kw=51.0,
)


run_case(
    name="Expensive Grid - Battery Support",
    telemetry={
        **base,
        "demand_kw": 70.0,
        "solar_generation_kw": 5.0,
        "battery_soc_percent": 80.0,
        "grid_price_inr_per_kwh": 11.0,
        "grid_carbon_intensity_g_per_kwh": 650.0,
    },
    action="DISCHARGE_BATTERY",
    predicted_demand_kw=75.0,
)


run_case(
    name="Solar Surplus - Charge Battery",
    telemetry={
        **base,
        "demand_kw": 25.0,
        "solar_generation_kw": 60.0,
        "battery_soc_percent": 40.0,
        "grid_price_inr_per_kwh": 5.0,
        "grid_carbon_intensity_g_per_kwh": 450.0,
    },
    action="CHARGE_BATTERY_FROM_SOLAR",
    predicted_demand_kw=25.0,
)


run_case(
    name="Cheap Grid - Charge Low Battery",
    telemetry={
        **base,
        "demand_kw": 30.0,
        "solar_generation_kw": 0.0,
        "battery_soc_percent": 25.0,
        "grid_price_inr_per_kwh": 3.5,
        "grid_carbon_intensity_g_per_kwh": 430.0,
    },
    action="CHARGE_BATTERY_FROM_GRID",
    predicted_demand_kw=30.0,
)


run_case(
    name="SOC Safety Boundary",
    telemetry={
        **base,
        "demand_kw": 80.0,
        "solar_generation_kw": 0.0,
        "battery_soc_percent": 20.2,
        "grid_price_inr_per_kwh": 12.0,
        "grid_carbon_intensity_g_per_kwh": 700.0,
    },
    action="DISCHARGE_BATTERY",
    predicted_demand_kw=85.0,
)


run_case(
    name="Emergency Load Shedding",
    telemetry={
        **base,
        "demand_kw": 100.0,
        "solar_generation_kw": 5.0,
        "battery_soc_percent": 15.0,
        "grid_price_inr_per_kwh": 13.5,
        "grid_carbon_intensity_g_per_kwh": 720.0,
    },
    action="SHED_NON_CRITICAL_LOAD",
    predicted_demand_kw=105.0,
)
