from __future__ import annotations

import os
from pathlib import Path


# ============================================================
# P_308 - Central Runtime Paths / Defaults
# ============================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

DATA_DIR = Path(
    os.getenv(
        "P308_DATA_DIR",
        str(PROJECT_ROOT / "data"),
    )
)

MODEL_DIR = Path(
    os.getenv(
        "P308_MODEL_DIR",
        str(PROJECT_ROOT / "models"),
    )
)

LOG_DIR = Path(
    os.getenv(
        "P308_LOG_DIR",
        str(PROJECT_ROOT / "logs"),
    )
)

DASHBOARD_DIR = Path(
    os.getenv(
        "P308_DASHBOARD_DIR",
        str(PROJECT_ROOT / "dashboard"),
    )
)

MQTT_CONFIG_FILE = Path(
    os.getenv(
        "P308_MQTT_CONFIG_FILE",
        str(
            PROJECT_ROOT
            / "mqtt"
            / "mosquitto.conf"
        ),
    )
)

FORECAST_MODEL_FILE = Path(
    os.getenv(
        "P308_FORECAST_MODEL_FILE",
        str(
            MODEL_DIR
            / "demand_forecaster.joblib"
        ),
    )
)

ANOMALY_MODEL_FILE = Path(
    os.getenv(
        "P308_ANOMALY_MODEL_FILE",
        str(
            MODEL_DIR
            / "energy_anomaly_detector.joblib"
        ),
    )
)

EVENT_DB_FILE = Path(
    os.getenv(
        "P308_EVENT_DB_FILE",
        str(
            DATA_DIR
            / "energy_events.db"
        ),
    )
)

TELEMETRY_CSV_FILE = Path(
    os.getenv(
        "P308_TELEMETRY_CSV_FILE",
        str(
            DATA_DIR
            / "telemetry.csv"
        ),
    )
)

DECISIONS_CSV_FILE = Path(
    os.getenv(
        "P308_DECISIONS_CSV_FILE",
        str(
            DATA_DIR
            / "decisions.csv"
        ),
    )
)


def ensure_runtime_directories() -> None:
    for directory in (
        DATA_DIR,
        MODEL_DIR,
        LOG_DIR,
        DASHBOARD_DIR,
    ):
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )
