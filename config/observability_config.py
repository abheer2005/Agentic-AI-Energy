from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

LOG_DIR = Path(
    os.getenv(
        "P308_LOG_DIR",
        str(PROJECT_ROOT / "logs"),
    )
)

LOG_LEVEL = os.getenv(
    "P308_LOG_LEVEL",
    "INFO",
).upper()

LOG_FILE_NAME = os.getenv(
    "P308_LOG_FILE_NAME",
    "agentic_energy_ai.log",
)

LOG_MAX_BYTES = int(
    os.getenv(
        "P308_LOG_MAX_BYTES",
        str(5 * 1024 * 1024),
    )
)

LOG_BACKUP_COUNT = int(
    os.getenv(
        "P308_LOG_BACKUP_COUNT",
        "5",
    )
)

# Health checks
MQTT_STALE_AFTER_SECONDS = int(
    os.getenv(
        "P308_MQTT_STALE_AFTER_SECONDS",
        "15",
    )
)

TELEMETRY_STALE_AFTER_SECONDS = int(
    os.getenv(
        "P308_TELEMETRY_STALE_AFTER_SECONDS",
        "15",
    )
)

# Prometheus
PROMETHEUS_ENABLED = os.getenv(
    "P308_PROMETHEUS_ENABLED",
    "true",
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
