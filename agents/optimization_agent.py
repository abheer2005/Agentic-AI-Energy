from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from config.optimization_config import (
    BATTERY_CAPACITY_KWH,
    MIN_SOC_PERCENT,
    MAX_SOC_PERCENT,
    TARGET_SOC_PERCENT,
    MAX_BATTERY_DISCHARGE_KW,
    MAX_BATTERY_CHARGE_KW,
    CHARGE_EFFICIENCY,
    DISCHARGE_EFFICIENCY,
    PLANNING_HORIZON_MINUTES,
    POWER_STEP_KW,
    PREPARE_LOAD_REDUCTION_FRACTION,
    EMERGENCY_LOAD_SHEDDING_FRACTION,
    REFERENCE_GRID_POWER_KW,
    REFERENCE_PRICE_INR_PER_KWH,
    REFERENCE_CARBON_G_PER_KWH,
    COST_WEIGHT,
    CARBON_WEIGHT,
    SOC_WEIGHT,
    BATTERY_WEAR_WEIGHT,
    SUPERVISOR_ALIGNMENT_WEIGHT,
)


@dataclass
class OptimizationAnalysis:
    recommended_battery_power_kw: float
    recommended_grid_import_kw: float
    estimated_grid_reduction_kw: float
    control_mode: str
    explanation: str

    # Advanced optimization/audit fields
    recommended_load_reduction_kw: float
    projected_soc_percent: float
    estimated_cost_inr_per_hour: float
    estimated_carbon_kg_per_hour: float
    objective_score: float
    planning_horizon_minutes: int
    battery_constraint_active: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OptimizationAgent:
    """
    Deterministic multi-objective energy optimizer.

    Sign convention:
        battery_power_kw > 0  -> discharge battery
        battery_power_kw < 0  -> charge battery
        battery_power_kw = 0  -> hold

    The optimizer performs a small deterministic candidate search over
    feasible battery powers. It minimizes a normalized objective containing:
        - grid-energy cost
        - grid carbon emissions
        - battery SOC deviation
        - battery cycling/wear
        - disagreement with the supervisor's high-level intent

    This is intentionally NOT delegated to an LLM.
    """

    def optimize(
        self,
        telemetry: dict[str, Any],
        supervisor_decision: Any,
        forecast_result: Any,
    ) -> OptimizationAnalysis:

        demand_kw = max(
            0.0,
            float(telemetry.get("demand_kw", 0.0)),
        )
        solar_kw = max(
            0.0,
            float(telemetry.get("solar_generation_kw", 0.0)),
        )
        soc_percent = self._clamp(
            float(telemetry.get("battery_soc_percent", TARGET_SOC_PERCENT)),
            0.0,
            100.0,
        )
        price = max(
            0.0,
            float(telemetry.get("grid_price_inr_per_kwh", 0.0)),
        )
        carbon = max(
            0.0,
            float(
                telemetry.get(
                    "grid_carbon_intensity_g_per_kwh",
                    0.0,
                )
            ),
        )

        action = self._read_value(
            supervisor_decision,
            "action",
            "MAINTAIN_CURRENT_OPERATION",
        )

        predicted_demand_kw = max(
            0.0,
            float(
                self._read_value(
                    forecast_result,
                    "predicted_demand_kw",
                    demand_kw,
                )
            ),
        )

        # MPC-style demand target:
        # use the larger of current and predicted demand when demand is rising,
        # otherwise use current demand so that the controller stays responsive.
        forecast_change_kw = predicted_demand_kw - demand_kw
        if forecast_change_kw > 2.0:
            planning_demand_kw = predicted_demand_kw
        else:
            planning_demand_kw = demand_kw

        load_reduction_kw = self._recommended_load_reduction(
            action=action,
            demand_kw=planning_demand_kw,
        )

        controlled_demand_kw = max(
            0.0,
            planning_demand_kw - load_reduction_kw,
        )

        base_grid_import_kw = max(
            controlled_demand_kw - solar_kw,
            0.0,
        )

        max_discharge_kw = self._max_sustainable_discharge_kw(
            soc_percent=soc_percent,
        )
        max_charge_kw = self._max_sustainable_charge_kw(
            soc_percent=soc_percent,
        )

        # Never charge from the grid unless the supervisor explicitly asks.
        allow_grid_charge = action == "CHARGE_BATTERY_FROM_GRID"

        # Solar charging may only consume available solar surplus.
        solar_surplus_kw = max(
            solar_kw - controlled_demand_kw,
            0.0,
        )

        if action == "CHARGE_BATTERY_FROM_SOLAR":
            max_charge_kw = min(
                max_charge_kw,
                solar_surplus_kw,
            )
        elif not allow_grid_charge:
            # For all non-grid-charging actions, charging is limited to
            # renewable surplus. This avoids accidental grid charging.
            max_charge_kw = min(
                max_charge_kw,
                solar_surplus_kw,
            )

        candidates = self._candidate_powers(
            max_charge_kw=max_charge_kw,
            max_discharge_kw=max_discharge_kw,
        )

        best = None

        for battery_power_kw in candidates:
            evaluation = self._evaluate_candidate(
                battery_power_kw=battery_power_kw,
                controlled_demand_kw=controlled_demand_kw,
                solar_kw=solar_kw,
                soc_percent=soc_percent,
                price=price,
                carbon=carbon,
                action=action,
                allow_grid_charge=allow_grid_charge,
            )

            if (
                best is None
                or evaluation["objective_score"]
                < best["objective_score"]
            ):
                best = evaluation

        assert best is not None

        recommended_battery_power_kw = round(
            best["battery_power_kw"],
            2,
        )
        recommended_grid_import_kw = round(
            best["grid_import_kw"],
            2,
        )

        # Compare against the same controlled load without battery support.
        estimated_grid_reduction_kw = round(
            max(
                0.0,
                base_grid_import_kw
                - recommended_grid_import_kw,
            ),
            2,
        )

        battery_constraint_active = (
            max_discharge_kw
            < MAX_BATTERY_DISCHARGE_KW - 1e-9
            or max_charge_kw
            < MAX_BATTERY_CHARGE_KW - 1e-9
        )

        control_mode = self._control_mode(
            action=action,
            battery_power_kw=recommended_battery_power_kw,
            load_reduction_kw=load_reduction_kw,
        )

        explanation = self._build_explanation(
            action=action,
            battery_power_kw=recommended_battery_power_kw,
            grid_import_kw=recommended_grid_import_kw,
            load_reduction_kw=load_reduction_kw,
            projected_soc_percent=best["projected_soc_percent"],
            price=price,
            carbon=carbon,
            battery_constraint_active=battery_constraint_active,
        )

        return OptimizationAnalysis(
            recommended_battery_power_kw=recommended_battery_power_kw,
            recommended_grid_import_kw=recommended_grid_import_kw,
            estimated_grid_reduction_kw=estimated_grid_reduction_kw,
            control_mode=control_mode,
            explanation=explanation,
            recommended_load_reduction_kw=round(
                load_reduction_kw,
                2,
            ),
            projected_soc_percent=round(
                best["projected_soc_percent"],
                3,
            ),
            estimated_cost_inr_per_hour=round(
                best["cost_inr_per_hour"],
                3,
            ),
            estimated_carbon_kg_per_hour=round(
                best["carbon_kg_per_hour"],
                3,
            ),
            objective_score=round(
                best["objective_score"],
                6,
            ),
            planning_horizon_minutes=PLANNING_HORIZON_MINUTES,
            battery_constraint_active=battery_constraint_active,
        )

    # ==========================================================
    # Candidate search
    # ==========================================================

    def _candidate_powers(
        self,
        max_charge_kw: float,
        max_discharge_kw: float,
    ) -> list[float]:

        candidates = {0.0}

        power = POWER_STEP_KW
        while power <= max_discharge_kw + 1e-9:
            candidates.add(round(power, 6))
            power += POWER_STEP_KW

        power = POWER_STEP_KW
        while power <= max_charge_kw + 1e-9:
            candidates.add(round(-power, 6))
            power += POWER_STEP_KW

        # Include exact bounds if they are not multiples of the step.
        if max_discharge_kw > 0:
            candidates.add(round(max_discharge_kw, 6))

        if max_charge_kw > 0:
            candidates.add(round(-max_charge_kw, 6))

        return sorted(candidates)

    def _evaluate_candidate(
        self,
        battery_power_kw: float,
        controlled_demand_kw: float,
        solar_kw: float,
        soc_percent: float,
        price: float,
        carbon: float,
        action: str,
        allow_grid_charge: bool,
    ) -> dict[str, float]:

        # Grid power after battery dispatch.
        grid_import_kw = max(
            controlled_demand_kw
            - solar_kw
            - battery_power_kw,
            0.0,
        )

        # Do not allow implicit grid charging unless explicitly requested.
        if (
            battery_power_kw < 0
            and not allow_grid_charge
        ):
            available_surplus_kw = max(
                solar_kw - controlled_demand_kw,
                0.0,
            )
            if abs(battery_power_kw) > available_surplus_kw + 1e-9:
                return {
                    "battery_power_kw": battery_power_kw,
                    "grid_import_kw": 1e9,
                    "projected_soc_percent": soc_percent,
                    "cost_inr_per_hour": 1e9,
                    "carbon_kg_per_hour": 1e9,
                    "objective_score": 1e9,
                }

        projected_soc_percent = self._project_soc(
            current_soc_percent=soc_percent,
            battery_power_kw=battery_power_kw,
        )

        cost_inr_per_hour = (
            grid_import_kw
            * price
        )

        carbon_kg_per_hour = (
            grid_import_kw
            * carbon
            / 1000.0
        )

        normalized_cost = (
            grid_import_kw
            / REFERENCE_GRID_POWER_KW
        ) * (
            price
            / REFERENCE_PRICE_INR_PER_KWH
        )

        normalized_carbon = (
            grid_import_kw
            / REFERENCE_GRID_POWER_KW
        ) * (
            carbon
            / REFERENCE_CARBON_G_PER_KWH
        )

        normalized_soc_penalty = (
            abs(
                projected_soc_percent
                - TARGET_SOC_PERCENT
            )
            / max(
                TARGET_SOC_PERCENT - MIN_SOC_PERCENT,
                MAX_SOC_PERCENT - TARGET_SOC_PERCENT,
                1.0,
            )
        )

        normalized_wear = (
            abs(battery_power_kw)
            / max(
                MAX_BATTERY_DISCHARGE_KW,
                MAX_BATTERY_CHARGE_KW,
            )
        )

        alignment_penalty = self._supervisor_alignment_penalty(
            action=action,
            battery_power_kw=battery_power_kw,
        )

        # Dynamic emphasis:
        # expensive / dirty grid makes import avoidance more important.
        price_factor = self._clamp(
            price / REFERENCE_PRICE_INR_PER_KWH,
            0.5,
            1.75,
        )
        carbon_factor = self._clamp(
            carbon / REFERENCE_CARBON_G_PER_KWH,
            0.5,
            1.50,
        )

        objective_score = (
            COST_WEIGHT
            * price_factor
            * normalized_cost
            + CARBON_WEIGHT
            * carbon_factor
            * normalized_carbon
            + SOC_WEIGHT
            * normalized_soc_penalty
            + BATTERY_WEAR_WEIGHT
            * normalized_wear
            + SUPERVISOR_ALIGNMENT_WEIGHT
            * alignment_penalty
        )

        # Strong operational constraints expressed as deterministic penalties.
        if action in {
            "DISCHARGE_BATTERY",
            "REDUCE_GRID_IMPORT",
        } and battery_power_kw <= 0:
            objective_score += 0.35

        if action == "PREPARE_BATTERY_SUPPORT" and battery_power_kw < 0:
            objective_score += 0.35

        if action in {
            "CHARGE_BATTERY_FROM_SOLAR",
            "CHARGE_BATTERY_FROM_GRID",
        } and battery_power_kw >= 0:
            objective_score += 0.35

        if action == "PRESERVE_BATTERY":
            objective_score += (
                abs(battery_power_kw)
                / max(
                    MAX_BATTERY_DISCHARGE_KW,
                    MAX_BATTERY_CHARGE_KW,
                )
            ) * 0.50

        if action == "MAINTAIN_CURRENT_OPERATION":
            objective_score += (
                abs(battery_power_kw)
                / max(
                    MAX_BATTERY_DISCHARGE_KW,
                    MAX_BATTERY_CHARGE_KW,
                )
            ) * 0.30

        return {
            "battery_power_kw": battery_power_kw,
            "grid_import_kw": grid_import_kw,
            "projected_soc_percent": projected_soc_percent,
            "cost_inr_per_hour": cost_inr_per_hour,
            "carbon_kg_per_hour": carbon_kg_per_hour,
            "objective_score": objective_score,
        }

    # ==========================================================
    # Battery physics / constraints
    # ==========================================================

    def _max_sustainable_discharge_kw(
        self,
        soc_percent: float,
    ) -> float:

        usable_energy_kwh = max(
            0.0,
            (
                soc_percent
                - MIN_SOC_PERCENT
            )
            / 100.0
            * BATTERY_CAPACITY_KWH,
        )

        horizon_hours = (
            PLANNING_HORIZON_MINUTES
            / 60.0
        )

        if horizon_hours <= 0:
            return 0.0

        # Energy withdrawn from the battery is larger than AC output
        # because discharge efficiency is below 100%.
        sustainable_output_kw = (
            usable_energy_kwh
            * DISCHARGE_EFFICIENCY
            / horizon_hours
        )

        return self._clamp(
            sustainable_output_kw,
            0.0,
            MAX_BATTERY_DISCHARGE_KW,
        )

    def _max_sustainable_charge_kw(
        self,
        soc_percent: float,
    ) -> float:

        available_storage_kwh = max(
            0.0,
            (
                MAX_SOC_PERCENT
                - soc_percent
            )
            / 100.0
            * BATTERY_CAPACITY_KWH,
        )

        horizon_hours = (
            PLANNING_HORIZON_MINUTES
            / 60.0
        )

        if horizon_hours <= 0:
            return 0.0

        # Only CHARGE_EFFICIENCY of input energy reaches the battery.
        sustainable_input_kw = (
            available_storage_kwh
            / CHARGE_EFFICIENCY
            / horizon_hours
        )

        return self._clamp(
            sustainable_input_kw,
            0.0,
            MAX_BATTERY_CHARGE_KW,
        )

    def _project_soc(
        self,
        current_soc_percent: float,
        battery_power_kw: float,
    ) -> float:

        horizon_hours = (
            PLANNING_HORIZON_MINUTES
            / 60.0
        )

        if battery_power_kw > 0:
            battery_energy_used_kwh = (
                battery_power_kw
                * horizon_hours
                / DISCHARGE_EFFICIENCY
            )

            soc_delta = (
                battery_energy_used_kwh
                / BATTERY_CAPACITY_KWH
                * 100.0
            )

            projected = (
                current_soc_percent
                - soc_delta
            )

        elif battery_power_kw < 0:
            input_energy_kwh = (
                abs(battery_power_kw)
                * horizon_hours
            )

            stored_energy_kwh = (
                input_energy_kwh
                * CHARGE_EFFICIENCY
            )

            soc_delta = (
                stored_energy_kwh
                / BATTERY_CAPACITY_KWH
                * 100.0
            )

            projected = (
                current_soc_percent
                + soc_delta
            )

        else:
            projected = current_soc_percent

        return self._clamp(
            projected,
            MIN_SOC_PERCENT,
            MAX_SOC_PERCENT,
        )

    # ==========================================================
    # Load control
    # ==========================================================

    def _recommended_load_reduction(
        self,
        action: str,
        demand_kw: float,
    ) -> float:

        if action == "SHED_NON_CRITICAL_LOAD":
            return (
                demand_kw
                * EMERGENCY_LOAD_SHEDDING_FRACTION
            )

        if action == "PREPARE_LOAD_REDUCTION":
            return (
                demand_kw
                * PREPARE_LOAD_REDUCTION_FRACTION
            )

        return 0.0

    # ==========================================================
    # Supervisor alignment
    # ==========================================================

    def _supervisor_alignment_penalty(
        self,
        action: str,
        battery_power_kw: float,
    ) -> float:

        max_power = max(
            MAX_BATTERY_DISCHARGE_KW,
            MAX_BATTERY_CHARGE_KW,
        )

        normalized_power = (
            abs(battery_power_kw)
            / max_power
        )

        if action in {
            "DISCHARGE_BATTERY",
            "REDUCE_GRID_IMPORT",
        }:
            if battery_power_kw > 0:
                return 1.0 - min(
                    battery_power_kw
                    / MAX_BATTERY_DISCHARGE_KW,
                    1.0,
                )
            return 1.0

        if action == "PREPARE_BATTERY_SUPPORT":
            if battery_power_kw >= 0:
                # Moderate support preferred rather than max discharge.
                target = (
                    0.35
                    * MAX_BATTERY_DISCHARGE_KW
                )
                return min(
                    abs(
                        battery_power_kw
                        - target
                    )
                    / MAX_BATTERY_DISCHARGE_KW,
                    1.0,
                )
            return 1.0

        if action in {
            "CHARGE_BATTERY_FROM_SOLAR",
            "CHARGE_BATTERY_FROM_GRID",
        }:
            if battery_power_kw < 0:
                return 1.0 - min(
                    abs(battery_power_kw)
                    / MAX_BATTERY_CHARGE_KW,
                    1.0,
                )
            return 1.0

        if action in {
            "PRESERVE_BATTERY",
            "MAINTAIN_CURRENT_OPERATION",
            "USE_SOLAR_FOR_LOAD",
            "PRIORITIZE_SOLAR",
            "PREPARE_LOAD_REDUCTION",
            "SHED_NON_CRITICAL_LOAD",
        }:
            return normalized_power

        return normalized_power

    # ==========================================================
    # Output helpers
    # ==========================================================

    def _control_mode(
        self,
        action: str,
        battery_power_kw: float,
        load_reduction_kw: float,
    ) -> str:

        if load_reduction_kw > 0:
            if action == "SHED_NON_CRITICAL_LOAD":
                return "EMERGENCY_LOAD_SHEDDING"
            return "LOAD_REDUCTION"

        if battery_power_kw > 0.01:
            return "BATTERY_DISCHARGE"

        if battery_power_kw < -0.01:
            if action == "CHARGE_BATTERY_FROM_SOLAR":
                return "SOLAR_BATTERY_CHARGE"
            return "BATTERY_CHARGE"

        if action in {
            "USE_SOLAR_FOR_LOAD",
            "PRIORITIZE_SOLAR",
        }:
            return "SOLAR_PRIORITY"

        if action == "PRESERVE_BATTERY":
            return "BATTERY_PRESERVATION"

        return "HOLD"

    def _build_explanation(
        self,
        action: str,
        battery_power_kw: float,
        grid_import_kw: float,
        load_reduction_kw: float,
        projected_soc_percent: float,
        price: float,
        carbon: float,
        battery_constraint_active: bool,
    ) -> str:

        components = [
            (
                f"Supervisor action={action}; "
                f"optimized battery dispatch={battery_power_kw:.2f} kW; "
                f"load reduction={load_reduction_kw:.2f} kW; "
                f"projected grid import={grid_import_kw:.2f} kW."
            ),
            (
                f"15-minute projected battery SOC="
                f"{projected_soc_percent:.2f}%."
            ),
            (
                f"Objective jointly considers grid cost "
                f"(₹{price:.2f}/kWh), carbon intensity "
                f"({carbon:.1f} gCO2/kWh), SOC reserve, "
                f"battery cycling, and supervisor intent."
            ),
        ]

        if battery_constraint_active:
            components.append(
                "Battery dispatch was bounded by SOC/energy or charging constraints."
            )

        return " ".join(components)

    @staticmethod
    def _read_value(
        source: Any,
        key: str,
        default: Any,
    ) -> Any:

        if isinstance(source, dict):
            return source.get(
                key,
                default,
            )

        return getattr(
            source,
            key,
            default,
        )

    @staticmethod
    def _clamp(
        value: float,
        minimum: float,
        maximum: float,
    ) -> float:

        return max(
            minimum,
            min(
                value,
                maximum,
            ),
        )
