from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class LoadAnalysis:
    status: str
    score: float
    demand_kw: float
    occupancy_percent: float
    temperature_c: float
    explanation: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LoadAgent:
    """
    Analyses building electricity demand using
    demand, occupancy and temperature context.
    """

    def __init__(self) -> None:
        self.low_threshold = 20.0
        self.normal_threshold = 40.0
        self.high_threshold = 60.0

    def analyze(
        self,
        telemetry: dict[str, Any]
    ) -> LoadAnalysis:

        demand = float(
            telemetry.get("demand_kw", 0.0)
        )

        occupancy = float(
            telemetry.get("occupancy_percent", 0.0)
        )

        temperature = float(
            telemetry.get("temperature_c", 25.0)
        )

        score = self._calculate_load_score(
            demand,
            occupancy,
            temperature
        )

        status = self._classify(score)

        explanation = self._build_explanation(
            demand=demand,
            occupancy=occupancy,
            temperature=temperature,
            status=status,
        )

        recommendation = self._recommend(
            status
        )

        return LoadAnalysis(
            status=status,
            score=round(score, 2),
            demand_kw=round(demand, 2),
            occupancy_percent=round(
                occupancy,
                2
            ),
            temperature_c=round(
                temperature,
                2
            ),
            explanation=explanation,
            recommendation=recommendation,
        )

    def _calculate_load_score(
        self,
        demand: float,
        occupancy: float,
        temperature: float
    ) -> float:

        # -------------------------------
        # Demand contribution
        # -------------------------------

        demand_score = min(
            demand / 80.0,
            1.0
        ) * 70

        # -------------------------------
        # Occupancy contribution
        # -------------------------------

        occupancy_score = min(
            occupancy / 100.0,
            1.0
        ) * 20

        # -------------------------------
        # HVAC temperature pressure
        # -------------------------------

        temperature_pressure = max(
            0.0,
            temperature - 24.0
        )

        temperature_score = min(
            temperature_pressure / 12.0,
            1.0
        ) * 10

        total_score = (
            demand_score
            + occupancy_score
            + temperature_score
        )

        return min(total_score, 100.0)

    def _classify(
        self,
        score: float
    ) -> str:

        if score < 25:
            return "LOW"

        if score < 50:
            return "NORMAL"

        if score < 75:
            return "HIGH"

        return "CRITICAL"

    def _build_explanation(
        self,
        demand: float,
        occupancy: float,
        temperature: float,
        status: str
    ) -> str:

        return (
            f"Building demand is {demand:.2f} kW "
            f"with {occupancy:.2f}% occupancy "
            f"and temperature {temperature:.2f} °C. "
            f"Combined load condition is {status}."
        )

    def _recommend(
        self,
        status: str
    ) -> str:

        recommendations = {
            "LOW":
                "No corrective action required.",

            "NORMAL":
                "Continue normal operation and monitor load.",

            "HIGH":
                "Reduce non-critical loads and inspect HVAC usage.",

            "CRITICAL":
                "Initiate load shedding for non-essential systems "
                "and prioritize critical equipment.",
        }

        return recommendations[status]