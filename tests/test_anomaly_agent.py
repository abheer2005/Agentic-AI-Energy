import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from agents.anomaly_agent import (
    AnomalyAgent,
)


agent = AnomalyAgent()


def run_scenario(
    name: str,
    telemetry: dict,
) -> None:

    print(
        "\n"
        + "=" * 75
    )

    print(
        f"TEST: {name}"
    )

    print(
        "=" * 75
    )

    result = agent.analyze(
        telemetry
    )

    print(
        f"Status            : "
        f"{result.status}"
    )

    print(
        f"Anomaly Count     : "
        f"{result.anomaly_count}"
    )

    print(
        f"Highest Severity  : "
        f"{result.highest_severity}"
    )

    if not result.events:

        print(
            "No anomalies detected."
        )

        return

    for index, event in enumerate(
        result.events,
        start=1,
    ):

        print(
            f"\nAnomaly #{index}"
        )

        print(
            f"Type            : "
            f"{event['anomaly_type']}"
        )

        print(
            f"Severity        : "
            f"{event['severity']}"
        )

        print(
            f"Message         : "
            f"{event['message']}"
        )

        print(
            f"Recommendation  : "
            f"{event['recommendation']}"
        )


# ==========================================================
# BASE NORMAL TELEMETRY
# ==========================================================

normal = {

    "timestamp":
        "2026-06-15T14:00:00",

    "demand_kw":
        55.0,

    "solar_generation_kw":
        50.0,

    "battery_soc_percent":
        70.0,

    "grid_price_inr_per_kwh":
        7.5,

    "grid_carbon_intensity_g_per_kwh":
        450.0,

    "temperature_c":
        31.0,

    "humidity_percent":
        60.0,

    "net_grid_demand_kw":
        5.0,
}


run_scenario(
    "Normal Operation",
    normal,
)


# ==========================================================
# HIGH DEMAND
# ==========================================================

scenario = normal.copy()

scenario[
    "demand_kw"
] = 82.0

scenario[
    "net_grid_demand_kw"
] = 70.0

run_scenario(
    "High Demand + High Grid Dependency",
    scenario,
)


# ==========================================================
# CRITICAL BATTERY
# ==========================================================

scenario = normal.copy()

scenario[
    "battery_soc_percent"
] = 12.0

run_scenario(
    "Critical Battery",
    scenario,
)


# ==========================================================
# EXTREME PRICE
# ==========================================================

scenario = normal.copy()

scenario[
    "grid_price_inr_per_kwh"
] = 14.5

run_scenario(
    "Extreme Grid Price",
    scenario,
)


# ==========================================================
# SOLAR ANOMALY
# ==========================================================

scenario = normal.copy()

scenario[
    "solar_generation_kw"
] = 2.0

run_scenario(
    "Low Daytime Solar",
    scenario,
)


# ==========================================================
# MULTIPLE CRITICAL CONDITIONS
# ==========================================================

scenario = normal.copy()

scenario.update(
    {
        "demand_kw": 96.0,
        "battery_soc_percent": 11.0,
        "grid_price_inr_per_kwh": 14.0,
        "grid_carbon_intensity_g_per_kwh": 720.0,
        "temperature_c": 43.0,
        "humidity_percent": 88.0,
        "solar_generation_kw": 1.0,
        "net_grid_demand_kw": 90.0,
    }
)

run_scenario(
    "Multiple Critical Conditions",
    scenario,
)