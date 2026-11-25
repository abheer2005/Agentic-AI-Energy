from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)


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

MODEL_FILE = (
    MODEL_DIR
    / "demand_forecaster.joblib"
)


FEATURES = [
    "hour",
    "day_of_week",
    "occupancy_percent",
    "temperature_c",
    "humidity_percent",
    "cloud_cover_percent",
    "solar_generation_kw",
    "grid_price_inr_per_kwh",
    "demand_kw",
]

TARGET = "future_demand_kw"


def main() -> None:

    print(
        "\n🧠 Training 15-Minute Ahead "
        "Demand Forecasting Model..."
    )

    dataframe = pd.read_csv(
        DATA_FILE
    )

    # ------------------------------------------------------
    # Create future target:
    # current row t predicts demand at t + 15 minutes
    # ------------------------------------------------------

    dataframe[TARGET] = (
        dataframe["demand_kw"]
        .shift(-1)
    )

    # Last row has no future observation.
    dataframe = dataframe.dropna().reset_index(
        drop=True
    )

    # ------------------------------------------------------
    # Chronological 80/20 split
    # ------------------------------------------------------

    split_index = int(
        len(dataframe) * 0.8
    )

    train_df = dataframe.iloc[
        :split_index
    ]

    test_df = dataframe.iloc[
        split_index:
    ]

    X_train = train_df[
        FEATURES
    ]

    y_train = train_df[
        TARGET
    ]

    X_test = test_df[
        FEATURES
    ]

    y_test = test_df[
        TARGET
    ]

    model = RandomForestRegressor(
        n_estimators=250,
        max_depth=14,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train,
        y_train
    )

    predictions = model.predict(
        X_test
    )

    mae = mean_absolute_error(
        y_test,
        predictions
    )

    rmse = mean_squared_error(
        y_test,
        predictions
    ) ** 0.5

    r2 = r2_score(
        y_test,
        predictions
    )

    print(
        "\n========== MODEL EVALUATION =========="
    )

    print(
        f"Forecast horizon: 15 minutes"
    )

    print(
        f"Training rows   : {len(train_df):,}"
    )

    print(
        f"Testing rows    : {len(test_df):,}"
    )

    print(
        f"MAE             : {mae:.3f} kW"
    )

    print(
        f"RMSE            : {rmse:.3f} kW"
    )

    print(
        f"R² Score        : {r2:.4f}"
    )

    print(
        "======================================"
    )

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    model_bundle = {
        "model": model,
        "features": FEATURES,
        "forecast_horizon_minutes": 15,
        "metrics": {
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
        },
    }

    joblib.dump(
        model_bundle,
        MODEL_FILE
    )

    print(
        f"\n✅ Model saved → {MODEL_FILE}"
    )


if __name__ == "__main__":
    main()