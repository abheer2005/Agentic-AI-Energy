from __future__ import annotations

import math
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "historical_energy_data.csv"
)

random.seed(42)


def occupancy_profile(hour: float) -> float:

    if 0 <= hour < 6:
        base = 3

    elif 6 <= hour < 9:
        base = 20

    elif 9 <= hour < 17:
        base = 75

    elif 17 <= hour < 21:
        base = 40

    else:
        base = 10

    return max(
        0,
        min(
            100,
            base + random.gauss(0, 5)
        )
    )


def temperature_profile(
    hour: float,
    day_index: int
) -> float:

    daily_cycle = (
        6
        * math.sin(
            (hour - 8)
            / 24
            * 2
            * math.pi
        )
    )

    long_term_variation = (
        2
        * math.sin(
            day_index
            / 30
            * 2
            * math.pi
        )
    )

    return (
        28
        + daily_cycle
        + long_term_variation
        + random.gauss(0, 0.8)
    )


def solar_profile(
    hour: float,
    cloud_cover: float
) -> float:

    if hour < 6 or hour > 18:
        return 0.0

    daylight_factor = math.sin(
        math.pi
        * (hour - 6)
        / 12
    )

    cloud_factor = (
        1
        - 0.75
        * cloud_cover
        / 100
    )

    generation = (
        80
        * daylight_factor
        * cloud_factor
    )

    return max(
        0,
        generation
        + random.gauss(0, 2)
    )


def grid_price(
    hour: float,
    demand: float
) -> float:

    if 18 <= hour < 22:
        base = 7.2

    elif 9 <= hour < 18:
        base = 5.8

    elif 0 <= hour < 6:
        base = 4.2

    else:
        base = 5.0

    demand_pressure = (
        max(
            demand - 40,
            0
        )
        * 0.025
    )

    return max(
        3,
        base
        + demand_pressure
        + random.gauss(0, 0.15)
    )


def generate_dataset(
    days: int = 90
) -> pd.DataFrame:

    rows = []

    start_time = datetime(
        2026,
        1,
        1,
        0,
        0
    )

    previous_demand = 25.0

    total_intervals = (
        days
        * 24
        * 4
    )

    for interval in range(
        total_intervals
    ):

        timestamp = (
            start_time
            + timedelta(
                minutes=15
                * interval
            )
        )

        hour = (
            timestamp.hour
            + timestamp.minute / 60
        )

        day_index = (
            timestamp
            - start_time
        ).days

        occupancy = occupancy_profile(
            hour
        )

        temperature = temperature_profile(
            hour,
            day_index
        )

        humidity = max(
            25,
            min(
                90,
                72
                - 0.8
                * (
                    temperature
                    - 20
                )
                + random.gauss(
                    0,
                    3
                )
            )
        )

        cloud_cover = max(
            0,
            min(
                100,
                50
                + 30
                * math.sin(
                    day_index
                    / 5
                )
                + random.gauss(
                    0,
                    15
                )
            )
        )

        solar = solar_profile(
            hour,
            cloud_cover
        )

        cooling_load = max(
            temperature - 24,
            0
        ) * 1.7

        occupancy_load = (
            occupancy
            * 0.32
        )

        time_load = (
            8
            if 9 <= hour < 18
            else 2
        )

        raw_demand = (
            18
            + occupancy_load
            + cooling_load
            + time_load
            + random.gauss(
                0,
                2
            )
        )

        # Adds temporal continuity.
        demand = (
            0.75
            * raw_demand
            + 0.25
            * previous_demand
        )

        demand = max(
            10,
            min(
                90,
                demand
            )
        )

        price = grid_price(
            hour,
            demand
        )

        carbon = (
            470
            + (
                70
                if 18 <= hour < 22
                else 0
            )
            + random.gauss(
                0,
                20
            )
        )

        net_grid = max(
            demand - solar,
            0
        )

        rows.append(
            {
                "timestamp": timestamp.isoformat(),
                "hour": hour,
                "day_of_week": timestamp.weekday(),
                "occupancy_percent": round(
                    occupancy,
                    2
                ),
                "temperature_c": round(
                    temperature,
                    2
                ),
                "humidity_percent": round(
                    humidity,
                    2
                ),
                "cloud_cover_percent": round(
                    cloud_cover,
                    2
                ),
                "solar_generation_kw": round(
                    solar,
                    2
                ),
                "grid_price_inr_per_kwh": round(
                    price,
                    2
                ),
                "grid_carbon_intensity_g_per_kwh": round(
                    carbon,
                    2
                ),
                "demand_kw": round(
                    demand,
                    2
                ),
                "previous_demand_kw": round(
                    previous_demand,
                    2
                ),
                "net_grid_demand_kw": round(
                    net_grid,
                    2
                ),
            }
        )

        previous_demand = demand

    return pd.DataFrame(
        rows
    )


def main() -> None:

    print(
        "\n⚡ Generating historical energy dataset..."
    )

    dataframe = generate_dataset(
        days=90
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    dataframe.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        f"✅ Generated {len(dataframe):,} readings"
    )

    print(
        f"💾 Saved → {OUTPUT_FILE}"
    )

    print(
        "\nSample:"
    )

    print(
        dataframe.head()
    )


if __name__ == "__main__":
    main()