import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from agents.unified_anomaly_agent import (
    UnifiedAnomalyAgent,
)


agent = UnifiedAnomalyAgent()


def show(
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
        f"Overall Status       : "
        f"{result.overall_status}"
    )

    print(
        f"Highest Severity     : "
        f"{result.highest_severity}"
    )

    print(
        f"Rule Anomaly Count   : "
        f"{result.rule_anomaly_count}"
    )

    print(
        f"ML Status            : "
        f"{result.ml_status}"
    )

    print(
        f"ML Severity          : "
        f"{result.ml_severity}"
    )

    print(
        f"ML Decision Score    : "
        f"{result.ml_decision_score}"
    )

    print(
        f"Combined Alert Count : "
        f"{result.combined_alert_count}"
    )

    print(
        f"Summary              : "
        f"{result.summary}"
    )


# ==========================================================
# REAL NORMAL HISTORICAL SAMPLE
# ==========================================================

data = pd.read_csv(
    PROJECT_ROOT
    / "data"
    / "historical_energy_data.csv"
)

normal_row = data.iloc[
    len(data) // 2
].to_dict()

normal_row["battery_soc_percent"] = 70.0

show(
    "Historical Sample",
    normal_row,
)


# ==========================================================
# MULTI-FAULT ANOMALY
# ==========================================================

critical = {

    "timestamp":
        "2026-06-15T14:00:00",

    "occupancy_percent":
        95.0,

    "temperature_c":
        43.0,

    "humidity_percent":
        88.0,

    "cloud_cover_percent":
        95.0,

    "solar_generation_kw":
        1.0,

    "grid_price_inr_per_kwh":
        14.0,

    "grid_carbon_intensity_g_per_kwh":
        720.0,

    "demand_kw":
        110.0,

    "net_grid_demand_kw":
        105.0,

    "battery_soc_percent":
        12.0,
}

show(
    "Critical Combined Anomaly",
    critical,
)