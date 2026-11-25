import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from agents.load_agent import LoadAgent
from agents.battery_agent import BatteryAgent
from agents.pricing_agent import PricingAgent
from agents.solar_agent import SolarAgent
from agents.grid_agent import GridAgent
from agents.supervisor_agent import SupervisorAgent
from agents.forecasting_agent import ForecastingAgent

sample_telemetry = {
    "demand_kw": 28.5,
    "solar_generation_kw": 0.0,
    "battery_soc_percent": 72.0,
    "grid_price_inr_per_kwh": 4.8,
    "grid_carbon_intensity_g_per_kwh": 520.0,
    "temperature_c": 22.0,
    "occupancy_percent": 4.0,
    "net_grid_demand_kw": 28.5,
}


load_agent = LoadAgent()
battery_agent = BatteryAgent()
pricing_agent = PricingAgent()
solar_agent = SolarAgent()
grid_agent = GridAgent()

supervisor = SupervisorAgent()
forecasting_agent = ForecastingAgent()


load_result = load_agent.analyze(sample_telemetry)
battery_result = battery_agent.analyze(sample_telemetry)
pricing_result = pricing_agent.analyze(sample_telemetry)
solar_result = solar_agent.analyze(sample_telemetry)
grid_result = grid_agent.analyze(sample_telemetry)
forecast_result = forecasting_agent.analyze(
    sample_telemetry
)


decision = supervisor.decide(
    load_result=load_result,
    battery_result=battery_result,
    pricing_result=pricing_result,
    solar_result=solar_result,
    grid_result=grid_result,
    forecast_result=forecast_result,
)


print("\n========== SUPERVISOR DECISION ==========\n")

print("LOAD")
print(load_result.to_dict())

print("\nBATTERY")
print(battery_result.to_dict())

print("\nPRICING")
print(pricing_result.to_dict())

print("\nSOLAR")
print(solar_result.to_dict())

print("\nGRID")
print(grid_result.to_dict())

print("\nFINAL DECISION")
print(decision.to_dict())

print("\n=========================================")