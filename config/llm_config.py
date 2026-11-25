from __future__ import annotations

import os


# ============================================================
# P_308 - Local LLM Configuration
# ============================================================

# The local LLM is an explanation/coordination layer ONLY.
# It never directly controls battery power, grid import, or load shedding.
LLM_ENABLED = os.getenv(
    "P308_LLM_ENABLED",
    "true",
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

OLLAMA_BASE_URL = os.getenv(
    "P308_OLLAMA_BASE_URL",
    "http://127.0.0.1:11434",
).rstrip("/")

# Small enough for a typical student laptop while still good at structured
# summaries. You can change it later without touching application code.
OLLAMA_MODEL = os.getenv(
    "P308_OLLAMA_MODEL",
    "qwen2.5:3b",
)

LLM_TIMEOUT_SECONDS = float(
    os.getenv(
        "P308_LLM_TIMEOUT_SECONDS",
        "20",
    )
)

LLM_TEMPERATURE = float(
    os.getenv(
        "P308_LLM_TEMPERATURE",
        "0.1",
    )
)

# Do not call the LLM for every 2-second telemetry packet.
# Generate immediately on meaningful state changes, otherwise periodically.
LLM_SUMMARY_INTERVAL_SECONDS = int(
    os.getenv(
        "P308_LLM_SUMMARY_INTERVAL_SECONDS",
        "60",
    )
)

LLM_MAX_RETRIES = int(
    os.getenv(
        "P308_LLM_MAX_RETRIES",
        "1",
    )
)

OLLAMA_KEEP_ALIVE = os.getenv(
    "P308_OLLAMA_KEEP_ALIVE",
    "10m",
)
