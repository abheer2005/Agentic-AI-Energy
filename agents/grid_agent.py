from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class GridAnalysis:
    status: str
    net_grid_demand_kw: float
    carbon_intensity: float
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GridAgent:
    """
    Analyses grid dependency and carbon intensity.
    """

    def analyze(
        self,
        telemetry: dict[str, Any]
    ) -> GridAnalysis:

        net_grid_demand = float(
            telemetry.get(
                "net_grid_demand_kw",
                0.0
            )
        )

        carbon_intensity = float(
            telemetry.get(
                "grid_carbon_intensity_g_per_kwh",
                0.0
            )
        )

        if net_grid_demand < 15:
            status = "LOW_DEPENDENCY"

        elif net_grid_demand < 35:
            status = "MODERATE_DEPENDENCY"

        elif net_grid_demand < 55:
            status = "HIGH_DEPENDENCY"

        else:
            status = "CRITICAL_DEPENDENCY"

        if carbon_intensity > 600:
            recommendation = (
                "Grid carbon intensity is high. "
                "Prefer renewable energy or battery support."
            )

        elif carbon_intensity > 450:
            recommendation = (
                "Grid carbon intensity is moderate. "
                "Reduce unnecessary grid consumption where possible."
            )

        else:
            recommendation = (
                "Grid carbon intensity is relatively low."
            )

        return GridAnalysis(
            status=status,
            net_grid_demand_kw=round(
                net_grid_demand,
                2
            ),
            carbon_intensity=round(
                carbon_intensity,
                2
            ),
            recommendation=recommendation,
        )