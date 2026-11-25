from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from agents.ml_anomaly_agent import MLAnomalyAgent


DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "historical_energy_data.csv"
)

MODEL_FILE = (
    PROJECT_ROOT
    / "models"
    / "energy_anomaly_detector.joblib"
)


agent = MLAnomalyAgent()


def print_result(
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
        f"Status         : {result.status}"
    )

    print(
        f"Anomaly Score  : {result.anomaly_score}"
    )

    print(
        f"Decision Score : {result.decision_score}"
    )

    print(
        f"Severity       : {result.severity}"
    )

    print(
        f"Recommendation : {result.recommendation}"
    )


# ==========================================================
# LOAD REAL HISTORICAL DATA
# ==========================================================

data = pd.read_csv(
    DATA_FILE
)

bundle = joblib.load(
    MODEL_FILE
)

model = bundle[
    "model"
]

features = bundle[
    "features"
]


# ==========================================================
# SCORE ALL TRAINING ROWS
# ==========================================================

X = data[
    features
].copy()

decision_scores = (
    model.decision_function(
        X
    )
)

data = data.copy()

data[
    "_decision_score"
] = decision_scores


# ==========================================================
# REPRESENTATIVE NORMAL SAMPLE
#
# Select a genuinely normal historical point rather than
# inventing one manually.
# ==========================================================

normal_rows = data[
    data[
        "_decision_score"
    ] > 0
].copy()

normal_rows = normal_rows.sort_values(
    "_decision_score",
    ascending=False,
)

representative_normal = (
    normal_rows
    .iloc[
        len(normal_rows) // 2
    ]
)

normal_telemetry = {
    feature: float(
        representative_normal[
            feature
        ]
    )
    for feature in features
}

print_result(
    "Real Historical Normal Pattern",
    normal_telemetry,
)


# ==========================================================
# MOST NORMAL TRAINING POINT
# ==========================================================

most_normal = (
    data
    .sort_values(
        "_decision_score",
        ascending=False,
    )
    .iloc[0]
)

most_normal_telemetry = {
    feature: float(
        most_normal[
            feature
        ]
    )
    for feature in features
}

print_result(
    "Most Normal Learned Pattern",
    most_normal_telemetry,
)


# ==========================================================
# STRONG MULTIVARIATE ANOMALY
# ==========================================================

strong_anomaly = {
    "occupancy_percent": 3.0,
    "temperature_c": 22.0,
    "humidity_percent": 50.0,
    "cloud_cover_percent": 10.0,
    "solar_generation_kw": 75.0,
    "grid_price_inr_per_kwh": 13.0,
    "grid_carbon_intensity_g_per_kwh": 700.0,
    "demand_kw": 95.0,
    "net_grid_demand_kw": 90.0,
}

print_result(
    "Strong Multivariate Anomaly",
    strong_anomaly,
)


# ==========================================================
# EXTREME SYSTEM STATE
# ==========================================================

extreme_state = {
    "occupancy_percent": 95.0,
    "temperature_c": 40.0,
    "humidity_percent": 85.0,
    "cloud_cover_percent": 95.0,
    "solar_generation_kw": 0.0,
    "grid_price_inr_per_kwh": 15.0,
    "grid_carbon_intensity_g_per_kwh": 750.0,
    "demand_kw": 120.0,
    "net_grid_demand_kw": 120.0,
}

print_result(
    "Extreme System State",
    extreme_state,
)


# ==========================================================
# SCORE DISTRIBUTION
# ==========================================================

print(
    "\n"
    + "=" * 75
)

print(
    "TRAINING DECISION-SCORE DISTRIBUTION"
)

print(
    "=" * 75
)

score_series = pd.Series(
    decision_scores
)

for percentile in [
    0.01,
    0.02,
    0.05,
    0.10,
    0.25,
    0.50,
    0.75,
    0.90,
    0.95,
    0.99,
]:

    value = score_series.quantile(
        percentile
    )

    print(
        f"{percentile * 100:>5.1f}th percentile : "
        f"{value:.6f}"
    )