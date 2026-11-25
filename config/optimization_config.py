from __future__ import annotations

# ============================================================
# P_308 - Optimization Configuration
# ============================================================

# Battery
BATTERY_CAPACITY_KWH = 150.0
MIN_SOC_PERCENT = 20.0
MAX_SOC_PERCENT = 95.0
TARGET_SOC_PERCENT = 65.0

MAX_BATTERY_DISCHARGE_KW = 40.0
MAX_BATTERY_CHARGE_KW = 30.0

CHARGE_EFFICIENCY = 0.95
DISCHARGE_EFFICIENCY = 0.95

# Model-predictive planning horizon.
# The controller still executes only the next command and recalculates
# when the next telemetry reading arrives.
PLANNING_HORIZON_MINUTES = 15

# Candidate resolution for deterministic search.
POWER_STEP_KW = 1.0

# Flexible-load control
PREPARE_LOAD_REDUCTION_FRACTION = 0.20
EMERGENCY_LOAD_SHEDDING_FRACTION = 0.30

# Operational reference values used only to normalize the objective.
REFERENCE_GRID_POWER_KW = 100.0
REFERENCE_PRICE_INR_PER_KWH = 8.0
REFERENCE_CARBON_G_PER_KWH = 600.0

# Multi-objective optimization weights.
COST_WEIGHT = 0.42
CARBON_WEIGHT = 0.28
SOC_WEIGHT = 0.14
BATTERY_WEAR_WEIGHT = 0.08
SUPERVISOR_ALIGNMENT_WEIGHT = 0.08
