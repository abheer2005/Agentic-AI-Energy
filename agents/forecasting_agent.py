from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODEL_FILE = (
    PROJECT_ROOT
    / "models"
    / "demand_forecaster.joblib"
)


@dataclass
class ForecastAnalysis:
    current_demand_kw: float
    predicted_demand_kw: float
    demand_change_kw: float
    forecast_horizon_minutes: int
    forecast_for_timestamp: str
    trend: str
    model_mae_kw: float
    model_rmse_kw: float
    model_r2: float
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ForecastingAgent:
    """
    Predicts building electricity demand 15 minutes ahead
    using the trained machine-learning forecasting model.
    """

    def __init__(self) -> None:

        if not MODEL_FILE.exists():
            raise FileNotFoundError(
                f"Forecasting model not found: {MODEL_FILE}"
            )

        bundle = joblib.load(
            MODEL_FILE
        )

        self.model = bundle["model"]
        self.features = bundle["features"]
        self.metrics = bundle["metrics"]

        self.forecast_horizon_minutes = bundle.get(
            "forecast_horizon_minutes",
            15,
        )

    def analyze(
        self,
        telemetry: dict[str, Any]
    ) -> ForecastAnalysis:

        # ------------------------------------------------------
        # Timestamp
        # ------------------------------------------------------

        timestamp_text = telemetry.get(
            "timestamp"
        )

        if timestamp_text:
            timestamp = datetime.fromisoformat(
                timestamp_text
            )
        else:
            timestamp = datetime.now()

        forecast_timestamp = (
            timestamp
            + timedelta(
                minutes=self.forecast_horizon_minutes
            )
        )

        hour = (
            timestamp.hour
            + timestamp.minute / 60
        )

        # ------------------------------------------------------
        # Current demand
        # ------------------------------------------------------

        current_demand = float(
            telemetry.get(
                "demand_kw",
                0.0
            )
        )

        # ------------------------------------------------------
        # ML feature construction
        #
        # All features represent information available
        # at current time t.
        # ------------------------------------------------------

        feature_row = {
            "hour": hour,

            "day_of_week": timestamp.weekday(),

            "occupancy_percent": float(
                telemetry.get(
                    "occupancy_percent",
                    0.0
                )
            ),

            "temperature_c": float(
                telemetry.get(
                    "temperature_c",
                    25.0
                )
            ),

            "humidity_percent": float(
                telemetry.get(
                    "humidity_percent",
                    50.0
                )
            ),

            "cloud_cover_percent": float(
                telemetry.get(
                    "cloud_cover_percent",
                    0.0
                )
            ),

            "solar_generation_kw": float(
                telemetry.get(
                    "solar_generation_kw",
                    0.0
                )
            ),

            "grid_price_inr_per_kwh": float(
                telemetry.get(
                    "grid_price_inr_per_kwh",
                    0.0
                )
            ),

            "demand_kw": current_demand,
        }

        input_df = pd.DataFrame(
            [feature_row],
            columns=self.features,
        )

        # ------------------------------------------------------
        # 15-minute-ahead prediction
        # ------------------------------------------------------

        predicted_demand = float(
            self.model.predict(
                input_df
            )[0]
        )

        demand_change = (
            predicted_demand
            - current_demand
        )

        trend = self._classify_trend(
            demand_change
        )

        recommendation = self._recommend(
            trend=trend,
            predicted_demand=predicted_demand,
        )

        return ForecastAnalysis(
            current_demand_kw=round(
                current_demand,
                2
            ),

            predicted_demand_kw=round(
                predicted_demand,
                2
            ),

            demand_change_kw=round(
                demand_change,
                2
            ),

            forecast_horizon_minutes=(
                self.forecast_horizon_minutes
            ),

            forecast_for_timestamp=(
                forecast_timestamp.isoformat()
            ),

            trend=trend,

            model_mae_kw=round(
                self.metrics["mae"],
                3
            ),

            model_rmse_kw=round(
                self.metrics["rmse"],
                3
            ),

            model_r2=round(
                self.metrics["r2"],
                4
            ),

            recommendation=recommendation,
        )

    def _classify_trend(
        self,
        change: float
    ) -> str:

        if change > 5:
            return "RISING_FAST"

        if change > 2:
            return "RISING"

        if change < -5:
            return "FALLING_FAST"

        if change < -2:
            return "FALLING"

        return "STABLE"

    def _recommend(
        self,
        trend: str,
        predicted_demand: float,
    ) -> str:

        if trend == "RISING_FAST":
            return (
                "Demand is expected to increase rapidly "
                "within the next 15 minutes. Prepare "
                "battery or renewable support."
            )

        if trend == "RISING":
            return (
                "Demand is expected to increase within "
                "the next 15 minutes. Monitor available "
                "energy resources."
            )

        if trend == "FALLING_FAST":
            return (
                "Demand is expected to decrease rapidly. "
                "Avoid unnecessary battery discharge."
            )

        if trend == "FALLING":
            return (
                "Demand is expected to decrease. Consider "
                "preserving stored battery energy."
            )

        return (
            "Demand is expected to remain relatively "
            "stable over the next 15 minutes."
        )