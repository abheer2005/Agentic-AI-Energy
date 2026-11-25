from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class SolarAnalysis:
    status: str
    generation_kw: float
    utilization_percent: float
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SolarAgent:
    """
    Analyses current solar generation relative
    to installed solar capacity.
    """

    MAX_SOLAR_CAPACITY_KW = 80.0

    def analyze(
        self,
        telemetry: dict[str, Any]
    ) -> SolarAnalysis:

        generation = float(
            telemetry.get(
                "solar_generation_kw",
                0.0
            )
        )

        utilization = (
            generation
            / self.MAX_SOLAR_CAPACITY_KW
        ) * 100

        utilization = max(
            0.0,
            min(
                utilization,
                100.0
            )
        )

        if generation <= 0.1:
            status = "NO_GENERATION"
            recommendation = (
                "No meaningful solar generation available."
            )

        elif utilization < 25:
            status = "LOW"
            recommendation = (
                "Solar generation is low. "
                "Continue relying on grid or battery support."
            )

        elif utilization < 60:
            status = "MODERATE"
            recommendation = (
                "Solar generation is useful. "
                "Use available solar for current demand."
            )

        elif utilization < 85:
            status = "HIGH"
            recommendation = (
                "Solar generation is strong. "
                "Reduce grid import and consider battery charging."
            )

        else:
            status = "EXCELLENT"
            recommendation = (
                "Solar production is near capacity. "
                "Prioritize renewable usage and battery charging."
            )

        return SolarAnalysis(
            status=status,
            generation_kw=round(
                generation,
                2
            ),
            utilization_percent=round(
                utilization,
                2
            ),
            recommendation=recommendation,
        )