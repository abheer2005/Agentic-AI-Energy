import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from agents.forecasting_agent import ForecastingAgent


sample_telemetry = {
    "timestamp": "2026-09-11T10:30:00",
    "demand_kw": 45.0,
    "solar_generation_kw": 35.0,
    "grid_price_inr_per_kwh": 5.8,
    "temperature_c": 31.0,
    "humidity_percent": 55.0,
    "occupancy_percent": 70.0,
    "cloud_cover_percent": 30.0,
}


agent = ForecastingAgent()

result = agent.analyze(
    sample_telemetry
)


print(
    "\n===== FORECASTING AGENT ====="
)

print(
    result.to_dict()
)