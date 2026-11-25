from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "historical_energy_data.csv"
)

MODEL_DIR = (
    PROJECT_ROOT
    / "models"
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

MODEL_FILE = (
    MODEL_DIR
    / "energy_anomaly_detector.joblib"
)


FEATURES = [
    "occupancy_percent",
    "temperature_c",
    "humidity_percent",
    "cloud_cover_percent",
    "solar_generation_kw",
    "grid_price_inr_per_kwh",
    "grid_carbon_intensity_g_per_kwh",
    "demand_kw",
    "net_grid_demand_kw",
]


def main() -> None:

    print(
        "Loading historical energy dataset..."
    )

    df = pd.read_csv(
        DATA_FILE
    )

    missing = [
        feature
        for feature in FEATURES
        if feature not in df.columns
    ]

    if missing:

        raise ValueError(
            f"Missing required columns: {missing}"
        )

    X = df[
        FEATURES
    ].copy()

    print(
        f"Training rows: {len(X):,}"
    )

    print(
        f"Features     : {len(FEATURES)}"
    )

    pipeline = Pipeline(
        steps=[
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "model",
                IsolationForest(
                    n_estimators=300,
                    contamination=0.02,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    pipeline.fit(
        X
    )

    training_predictions = (
        pipeline.predict(
            X
        )
    )

    anomaly_count = int(
        (
            training_predictions
            == -1
        ).sum()
    )

    anomaly_rate = (
        anomaly_count
        / len(X)
        * 100
    )

    bundle = {
        "model": pipeline,
        "features": FEATURES,
        "training_rows": len(X),
        "training_anomaly_count": anomaly_count,
        "training_anomaly_rate_percent": round(
            anomaly_rate,
            3,
        ),
        "model_type": "IsolationForest",
    }

    joblib.dump(
        bundle,
        MODEL_FILE,
    )

    print(
        "\nModel training complete."
    )

    print(
        f"Detected training anomalies : "
        f"{anomaly_count}"
    )

    print(
        f"Training anomaly rate       : "
        f"{anomaly_rate:.3f}%"
    )

    print(
        f"Saved model                 : "
        f"{MODEL_FILE}"
    )


if __name__ == "__main__":
    main()