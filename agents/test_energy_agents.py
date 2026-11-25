import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from agents.load_agent import LoadAgent
from agents.battery_agent import BatteryAgent
from agents.pricing_agent import PricingAgent
from agents.solar_agent import SolarAgent


sample_telemetry = {
    "demand_kw": 28.5,
    "solar_generation_kw": 0.0,
    "battery_soc_percent": 72.0,
    "grid_price_inr_per_kwh": 4.8,
    "temperature_c": 22.0,
    "occupancy_percent": 4.0,
}


load_agent = LoadAgent()
battery_agent = BatteryAgent()
pricing_agent = PricingAgent()
solar_agent = SolarAgent()


load_result = load_agent.analyze(
    sample_telemetry
)

battery_result = battery_agent.analyze(
    sample_telemetry
)

pricing_result = pricing_agent.analyze(
    sample_telemetry
)

solar_result = solar_agent.analyze(
    sample_telemetry
)


print("\n========== MULTI-AGENT ENERGY ANALYSIS ==========\n")

print("LOAD AGENT")
print(
    load_result.to_dict()
)

print("\nBATTERY AGENT")
print(
    battery_result.to_dict()
)

print("\nPRICING AGENT")
print(
    pricing_result.to_dict()
)

print("\nSOLAR AGENT")
print(
    solar_result.to_dict()
)

print("\n=================================================")