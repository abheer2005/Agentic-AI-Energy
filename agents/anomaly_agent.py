from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class AnomalyEvent:
    anomaly_type: str
    severity: str
    message: str
    observed_value: float
    threshold: float
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnomalyAnalysis:
    status: str
    anomaly_count: int
    highest_severity: str
    events: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AnomalyAgent:
    """
    Detects abnormal or risky operating conditions from
    smart-building energy telemetry.

    This first layer uses deterministic operational rules.
    Later we can additionally add statistical / ML anomaly detection.
    """

    # ======================================================
    # THRESHOLDS
    # ======================================================

    CRITICAL_DEMAND_KW = 90.0
    HIGH_DEMAND_KW = 75.0

    LOW_BATTERY_SOC = 25.0
    CRITICAL_BATTERY_SOC = 15.0

    HIGH_GRID_PRICE = 10.0
    EXTREME_GRID_PRICE = 13.0

    HIGH_CARBON_INTENSITY = 600.0
    EXTREME_CARBON_INTENSITY = 700.0

    HIGH_TEMPERATURE_C = 35.0
    EXTREME_TEMPERATURE_C = 42.0

    HIGH_HUMIDITY_PERCENT = 85.0

    HIGH_GRID_DEPENDENCY_KW = 65.0

    # Solar expected to be significant during strong daylight.
    DAYLIGHT_START_HOUR = 9.0
    DAYLIGHT_END_HOUR = 16.0
    LOW_DAYTIME_SOLAR_KW = 8.0

    # ======================================================
    # SEVERITY ORDER
    # ======================================================

    SEVERITY_RANK = {
        "NONE": 0,
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }

    # ======================================================
    # MAIN ANALYSIS
    # ======================================================

    def analyze(
        self,
        telemetry: dict[str, Any],
    ) -> AnomalyAnalysis:

        events: list[AnomalyEvent] = []

        demand = float(
            telemetry.get(
                "demand_kw",
                0.0,
            )
        )

        battery_soc_raw = telemetry.get(
            "battery_soc_percent"
        )

        battery_soc = (
            float(battery_soc_raw)
            if battery_soc_raw is not None
            else None
        )
        grid_price = float(
            telemetry.get(
                "grid_price_inr_per_kwh",
                0.0,
            )
        )

        carbon = float(
            telemetry.get(
                "grid_carbon_intensity_g_per_kwh",
                0.0,
            )
        )

        temperature = float(
            telemetry.get(
                "temperature_c",
                0.0,
            )
        )

        humidity = float(
            telemetry.get(
                "humidity_percent",
                0.0,
            )
        )

        solar = float(
            telemetry.get(
                "solar_generation_kw",
                0.0,
            )
        )

        grid_demand = float(
            telemetry.get(
                "net_grid_demand_kw",
                0.0,
            )
        )

        timestamp = str(
            telemetry.get(
                "timestamp",
                "",
            )
        )

        # ==================================================
        # DEMAND ANOMALY
        # ==================================================

        if demand >= self.CRITICAL_DEMAND_KW:

            events.append(
                AnomalyEvent(
                    anomaly_type="CRITICAL_DEMAND_SPIKE",
                    severity="CRITICAL",
                    message=(
                        f"Building demand reached "
                        f"{demand:.2f} kW."
                    ),
                    observed_value=demand,
                    threshold=self.CRITICAL_DEMAND_KW,
                    recommendation=(
                        "Immediately use battery support "
                        "and shed non-critical loads."
                    ),
                )
            )

        elif demand >= self.HIGH_DEMAND_KW:

            events.append(
                AnomalyEvent(
                    anomaly_type="HIGH_DEMAND",
                    severity="HIGH",
                    message=(
                        f"Building demand is unusually high "
                        f"at {demand:.2f} kW."
                    ),
                    observed_value=demand,
                    threshold=self.HIGH_DEMAND_KW,
                    recommendation=(
                        "Prepare battery support and review "
                        "high-consumption equipment."
                    ),
                )
            )

        # ==================================================
        # BATTERY ANOMALY
        # ==================================================

        if (
            battery_soc is not None
            and battery_soc <= self.CRITICAL_BATTERY_SOC
        ):

            events.append(
                AnomalyEvent(
                    anomaly_type="CRITICAL_BATTERY_SOC",
                    severity="CRITICAL",
                    message=(
                        f"Battery SOC has fallen to "
                        f"{battery_soc:.2f}%."
                    ),
                    observed_value=battery_soc,
                    threshold=self.CRITICAL_BATTERY_SOC,
                    recommendation=(
                        "Stop discretionary discharge and "
                        "prioritize battery charging."
                    ),
                )
            )

        elif (
            battery_soc is not None
            and battery_soc <= self.LOW_BATTERY_SOC
        ):

            events.append(
                AnomalyEvent(
                    anomaly_type="LOW_BATTERY_SOC",
                    severity="HIGH",
                    message=(
                        f"Battery SOC is low at "
                        f"{battery_soc:.2f}%."
                    ),
                    observed_value=battery_soc,
                    threshold=self.LOW_BATTERY_SOC,
                    recommendation=(
                        "Preserve battery energy and charge "
                        "when grid price or solar conditions permit."
                    ),
                )
            )

        # ==================================================
        # PRICE ANOMALY
        # ==================================================

        if grid_price >= self.EXTREME_GRID_PRICE:

            events.append(
                AnomalyEvent(
                    anomaly_type="EXTREME_GRID_PRICE",
                    severity="HIGH",
                    message=(
                        f"Grid tariff reached "
                        f"₹{grid_price:.2f}/kWh."
                    ),
                    observed_value=grid_price,
                    threshold=self.EXTREME_GRID_PRICE,
                    recommendation=(
                        "Minimize grid import using battery, "
                        "solar, or flexible-load reduction."
                    ),
                )
            )

        elif grid_price >= self.HIGH_GRID_PRICE:

            events.append(
                AnomalyEvent(
                    anomaly_type="HIGH_GRID_PRICE",
                    severity="MEDIUM",
                    message=(
                        f"Grid tariff is high at "
                        f"₹{grid_price:.2f}/kWh."
                    ),
                    observed_value=grid_price,
                    threshold=self.HIGH_GRID_PRICE,
                    recommendation=(
                        "Shift flexible demand or use stored "
                        "energy where economical."
                    ),
                )
            )

        # ==================================================
        # CARBON ANOMALY
        # ==================================================

        if carbon >= self.EXTREME_CARBON_INTENSITY:

            events.append(
                AnomalyEvent(
                    anomaly_type="EXTREME_GRID_CARBON",
                    severity="HIGH",
                    message=(
                        f"Grid carbon intensity reached "
                        f"{carbon:.2f} gCO₂/kWh."
                    ),
                    observed_value=carbon,
                    threshold=self.EXTREME_CARBON_INTENSITY,
                    recommendation=(
                        "Reduce grid consumption and prioritize "
                        "low-carbon energy sources."
                    ),
                )
            )

        elif carbon >= self.HIGH_CARBON_INTENSITY:

            events.append(
                AnomalyEvent(
                    anomaly_type="HIGH_GRID_CARBON",
                    severity="MEDIUM",
                    message=(
                        f"Grid carbon intensity is elevated at "
                        f"{carbon:.2f} gCO₂/kWh."
                    ),
                    observed_value=carbon,
                    threshold=self.HIGH_CARBON_INTENSITY,
                    recommendation=(
                        "Prefer solar or battery energy where feasible."
                    ),
                )
            )

        # ==================================================
        # TEMPERATURE ANOMALY
        # ==================================================

        if temperature >= self.EXTREME_TEMPERATURE_C:

            events.append(
                AnomalyEvent(
                    anomaly_type="EXTREME_TEMPERATURE",
                    severity="CRITICAL",
                    message=(
                        f"Temperature reached "
                        f"{temperature:.2f}°C."
                    ),
                    observed_value=temperature,
                    threshold=self.EXTREME_TEMPERATURE_C,
                    recommendation=(
                        "Inspect HVAC operation and protect "
                        "temperature-sensitive equipment."
                    ),
                )
            )

        elif temperature >= self.HIGH_TEMPERATURE_C:

            events.append(
                AnomalyEvent(
                    anomaly_type="HIGH_TEMPERATURE",
                    severity="MEDIUM",
                    message=(
                        f"Temperature is high at "
                        f"{temperature:.2f}°C."
                    ),
                    observed_value=temperature,
                    threshold=self.HIGH_TEMPERATURE_C,
                    recommendation=(
                        "Monitor HVAC load and cooling performance."
                    ),
                )
            )

        # ==================================================
        # HUMIDITY ANOMALY
        # ==================================================

        if humidity >= self.HIGH_HUMIDITY_PERCENT:

            events.append(
                AnomalyEvent(
                    anomaly_type="HIGH_HUMIDITY",
                    severity="MEDIUM",
                    message=(
                        f"Humidity reached "
                        f"{humidity:.2f}%."
                    ),
                    observed_value=humidity,
                    threshold=self.HIGH_HUMIDITY_PERCENT,
                    recommendation=(
                        "Inspect ventilation and dehumidification."
                    ),
                )
            )

        # ==================================================
        # GRID DEPENDENCY ANOMALY
        # ==================================================

        if grid_demand >= self.HIGH_GRID_DEPENDENCY_KW:

            events.append(
                AnomalyEvent(
                    anomaly_type="HIGH_GRID_DEPENDENCY",
                    severity="HIGH",
                    message=(
                        f"Grid import reached "
                        f"{grid_demand:.2f} kW."
                    ),
                    observed_value=grid_demand,
                    threshold=self.HIGH_GRID_DEPENDENCY_KW,
                    recommendation=(
                        "Increase renewable or battery contribution "
                        "and evaluate load reduction."
                    ),
                )
            )

        # ==================================================
        # DAYTIME SOLAR ANOMALY
        # ==================================================

        hour = self._extract_hour(
            timestamp
        )

        if (
            hour is not None
            and self.DAYLIGHT_START_HOUR
            <= hour
            <= self.DAYLIGHT_END_HOUR
            and solar
            < self.LOW_DAYTIME_SOLAR_KW
        ):

            events.append(
                AnomalyEvent(
                    anomaly_type="LOW_DAYTIME_SOLAR",
                    severity="MEDIUM",
                    message=(
                        f"Solar generation is only "
                        f"{solar:.2f} kW during daytime."
                    ),
                    observed_value=solar,
                    threshold=self.LOW_DAYTIME_SOLAR_KW,
                    recommendation=(
                        "Check cloud conditions, panel availability, "
                        "or possible solar-system faults."
                    ),
                )
            )

        # ==================================================
        # FINAL STATUS
        # ==================================================

        if not events:

            return AnomalyAnalysis(
                status="NORMAL",
                anomaly_count=0,
                highest_severity="NONE",
                events=[],
            )

        highest_severity = max(
            (
                event.severity
                for event in events
            ),
            key=lambda severity:
                self.SEVERITY_RANK[
                    severity
                ],
        )

        return AnomalyAnalysis(
            status="ANOMALY_DETECTED",
            anomaly_count=len(
                events
            ),
            highest_severity=highest_severity,
            events=[
                event.to_dict()
                for event in events
            ],
        )

    # ======================================================
    # TIME UTILITY
    # ======================================================

    @staticmethod
    def _extract_hour(
        timestamp: str,
    ) -> float | None:

        try:

            time_part = (
                timestamp
                .split("T")[1]
            )

            components = (
                time_part
                .split(":")
            )

            hour = int(
                components[0]
            )

            minute = int(
                components[1]
            )

            return (
                hour
                + minute / 60
            )

        except (
            IndexError,
            ValueError,
            AttributeError,
        ):

            return None