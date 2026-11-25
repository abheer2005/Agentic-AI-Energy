import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.energy_controller import EnergyController



def run_test(
    name: str,
    telemetry: dict,
) -> None:

    controller = EnergyController()

    result = controller.process(
        telemetry
    )

    print(
        "\n"
        + "=" * 70
    )

    print(
        f"SCENARIO: {name}"
    )

    print(
        "=" * 70
    )

    decision = result[
        "decision"
    ]

    optimization = result[
        "optimization"
    ]

    forecast = result[
        "agents"
    ]["forecast"]

    print(
        f"Current Demand   : "
        f"{telemetry['demand_kw']} kW"
    )

    print(
        f"Solar Generation : "
        f"{telemetry['solar_generation_kw']} kW"
    )

    print(
        f"Battery SOC      : "
        f"{telemetry['battery_soc_percent']}%"
    )

    print(
        f"Forecast Demand  : "
        f"{forecast['predicted_demand_kw']} kW"
    )

    print(
        f"\nSupervisor Action: "
        f"{decision['action']}"
    )

    print(
        f"Priority         : "
        f"{decision['priority']}"
    )

    print(
        "\nOPTIMIZATION"
    )

    print(
        f"Control Mode     : "
        f"{optimization['control_mode']}"
    )

    print(
        f"Battery Power    : "
        f"{optimization['recommended_battery_power_kw']} kW"
    )

    print(
        f"Grid Import      : "
        f"{optimization['recommended_grid_import_kw']} kW"
    )

    print(
        f"Grid Reduction   : "
        f"{optimization['estimated_grid_reduction_kw']} kW"
    )

    print(
        f"Explanation      : "
        f"{optimization['explanation']}"
    )


def main() -> None:

    scenarios = {

        "Expensive Grid + Healthy Battery": {

            "timestamp": "2026-06-15T19:00:00",

            "reading_id": 1,

            "demand_kw": 50.0,

            "solar_generation_kw": 5.0,

            "battery_soc_percent": 75.0,

            "grid_price_inr_per_kwh": 9.0,

            "grid_carbon_intensity_g_per_kwh": 500.0,

            "temperature_c": 30.0,

            "humidity_percent": 55.0,

            "occupancy_percent": 60.0,

            "cloud_cover_percent": 70.0,

            "net_grid_demand_kw": 45.0,
        },

        "Strong Solar + Low Battery": {

            "timestamp": "2026-06-15T13:00:00",

            "reading_id": 2,

            "demand_kw": 40.0,

            "solar_generation_kw": 70.0,

            "battery_soc_percent": 30.0,

            "grid_price_inr_per_kwh": 5.0,

            "grid_carbon_intensity_g_per_kwh": 350.0,

            "temperature_c": 32.0,

            "humidity_percent": 50.0,

            "occupancy_percent": 70.0,

            "cloud_cover_percent": 10.0,

            "net_grid_demand_kw": 0.0,
        },

        "Cheap Grid + Low Battery": {

            "timestamp": "2026-06-15T03:00:00",

            "reading_id": 3,

            "demand_kw": 28.0,

            "solar_generation_kw": 0.0,

            "battery_soc_percent": 30.0,

            "grid_price_inr_per_kwh": 3.5,

            "grid_carbon_intensity_g_per_kwh": 420.0,

            "temperature_c": 23.0,

            "humidity_percent": 62.0,

            "occupancy_percent": 10.0,

            "cloud_cover_percent": 25.0,

            "net_grid_demand_kw": 28.0,
        },

        "High Carbon Grid": {

            "timestamp": "2026-06-15T19:30:00",

            "reading_id": 4,

            "demand_kw": 35.0,

            "solar_generation_kw": 4.0,

            "battery_soc_percent": 70.0,

            "grid_price_inr_per_kwh": 5.2,

            "grid_carbon_intensity_g_per_kwh": 680.0,

            "temperature_c": 29.0,

            "humidity_percent": 55.0,

            "occupancy_percent": 45.0,

            "cloud_cover_percent": 65.0,

            "net_grid_demand_kw": 31.0,
        },
    }

    for name, telemetry in scenarios.items():

        run_test(
            name,
            telemetry,
        )


if __name__ == "__main__":
    main()