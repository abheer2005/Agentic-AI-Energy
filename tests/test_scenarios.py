import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from agents.load_agent import LoadAgent
from agents.battery_agent import BatteryAgent
from agents.pricing_agent import PricingAgent
from agents.solar_agent import SolarAgent
from agents.grid_agent import GridAgent
from agents.supervisor_agent import SupervisorAgent
from agents.forecasting_agent import ForecastingAgent


load_agent = LoadAgent()
battery_agent = BatteryAgent()
pricing_agent = PricingAgent()
solar_agent = SolarAgent()
grid_agent = GridAgent()
supervisor = SupervisorAgent()
forecasting_agent = ForecastingAgent()


def run_scenario(name: str, telemetry: dict) -> None:

    load_result = load_agent.analyze(telemetry)
    battery_result = battery_agent.analyze(telemetry)
    pricing_result = pricing_agent.analyze(telemetry)
    solar_result = solar_agent.analyze(telemetry)
    grid_result = grid_agent.analyze(telemetry)
    forecast_result = forecasting_agent.analyze(
        telemetry
    )

    decision = supervisor.decide(
        load_result=load_result,
        battery_result=battery_result,
        pricing_result=pricing_result,
        solar_result=solar_result,
        grid_result=grid_result,
        forecast_result=forecast_result,
    )

    print("\n" + "=" * 70)
    print(f"SCENARIO: {name}")
    print("=" * 70)

    print(f"Load Status     : {load_result.status}")
    print(f"Battery Status  : {battery_result.status}")
    print(f"Pricing Status  : {pricing_result.status}")
    print(f"Solar Status    : {solar_result.status}")
    print(f"Grid Status     : {grid_result.status}")
    print(f"Forecast Trend  : {forecast_result.trend}")
    print(f"Predicted Demand: {forecast_result.predicted_demand_kw} kW")

    print("\nFINAL DECISION")
    print(f"Action          : {decision.action}")
    print(f"Priority        : {decision.priority}")
    print(f"Confidence      : {decision.confidence}")
    print(f"Reason          : {decision.reason}")


scenarios = {

    "Normal Operation": {
        "demand_kw": 28.0,
        "solar_generation_kw": 0.0,
        "battery_soc_percent": 72.0,
        "grid_price_inr_per_kwh": 4.8,
        "grid_carbon_intensity_g_per_kwh": 520.0,
        "temperature_c": 22.0,
        "occupancy_percent": 5.0,
        "net_grid_demand_kw": 28.0,
        "timestamp": "2026-06-15T19:00:00",
    },
    

    "Very Expensive Grid + Healthy Battery": {
        "demand_kw": 42.0,
        "solar_generation_kw": 5.0,
        "battery_soc_percent": 75.0,
        "grid_price_inr_per_kwh": 8.5,
        "grid_carbon_intensity_g_per_kwh": 540.0,
        "temperature_c": 27.0,
        "occupancy_percent": 50.0,
        "net_grid_demand_kw": 37.0,
        "timestamp": "2026-06-15T19:00:00",
    },

    "Strong Solar + Low Battery": {
        "demand_kw": 35.0,
        "solar_generation_kw": 70.0,
        "battery_soc_percent": 25.0,
        "grid_price_inr_per_kwh": 5.0,
        "grid_carbon_intensity_g_per_kwh": 500.0,
        "temperature_c": 29.0,
        "occupancy_percent": 45.0,
        "net_grid_demand_kw": 0.0,
        "timestamp": "2026-06-15T13:00:00",
    },

    "Cheap Grid + Low Battery": {
        "demand_kw": 30.0,
        "solar_generation_kw": 0.0,
        "battery_soc_percent": 30.0,
        "grid_price_inr_per_kwh": 3.8,
        "grid_carbon_intensity_g_per_kwh": 430.0,
        "temperature_c": 24.0,
        "occupancy_percent": 30.0,
        "net_grid_demand_kw": 30.0,
        "timestamp": "2026-06-15T03:00:00",
    },

    "High Carbon Grid + Healthy Battery": {
        "demand_kw": 32.0,
        "solar_generation_kw": 4.0,
        "battery_soc_percent": 70.0,
        "grid_price_inr_per_kwh": 5.2,
        "grid_carbon_intensity_g_per_kwh": 680.0,
        "temperature_c": 26.0,
        "occupancy_percent": 35.0,
        "net_grid_demand_kw": 28.0,
        "timestamp": "2026-06-15T19:30:00",
    },

    "Critical Load + Healthy Battery": {
        "demand_kw": 78.0,
        "solar_generation_kw": 5.0,
        "battery_soc_percent": 80.0,
        "grid_price_inr_per_kwh": 6.5,
        "grid_carbon_intensity_g_per_kwh": 580.0,
        "temperature_c": 35.0,
        "occupancy_percent": 95.0,
        "net_grid_demand_kw": 73.0,
        "timestamp": "2026-06-15T16:00:00",
    },

    "Critical Load + Very Low Battery": {
        "demand_kw": 82.0,
        "solar_generation_kw": 2.0,
        "battery_soc_percent": 10.0,
        "grid_price_inr_per_kwh": 7.0,
        "grid_carbon_intensity_g_per_kwh": 610.0,
        "temperature_c": 36.0,
        "occupancy_percent": 98.0,
        "net_grid_demand_kw": 80.0,
        "timestamp": "2026-06-15T17:00:00",
    },
}


for scenario_name, telemetry in scenarios.items():
    run_scenario(
        scenario_name,
        telemetry
    )