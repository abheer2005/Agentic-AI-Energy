import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from agents.load_agent import LoadAgent


sample_telemetry = {
    "demand_kw": 28.5,
    "occupancy_percent": 4.0,
    "temperature_c": 22.0,
}


agent = LoadAgent()

result = agent.analyze(
    sample_telemetry
)


print("\n===== LOAD AGENT RESULT =====")

print(
    f"Status          : {result.status}"
)

print(
    f"Score           : {result.score}/100"
)

print(
    f"Demand          : {result.demand_kw} kW"
)

print(
    f"Occupancy       : {result.occupancy_percent}%"
)

print(
    f"Temperature     : {result.temperature_c} °C"
)

print(
    f"Explanation     : {result.explanation}"
)

print(
    f"Recommendation  : {result.recommendation}"
)