from __future__ import annotations

import os


# ============================================================
# P_308 - FastAPI Backend Configuration
# ============================================================

API_HOST = os.getenv(
    "P308_API_HOST",
    "127.0.0.1",
)

API_PORT = int(
    os.getenv(
        "P308_API_PORT",
        "8000",
    )
)

API_TITLE = "P_308 Agentic Energy AI API"
API_VERSION = "1.0.0"

# Browser dashboard origins planned for Step 6.
# Keep localhost development easy without opening the API to every origin.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "P308_CORS_ORIGINS",
        (
            "http://127.0.0.1:3000,"
            "http://localhost:3000,"
            "http://127.0.0.1:5173,"
            "http://localhost:5173,"
            "http://127.0.0.1:8000,"
            "http://localhost:8000"
        ),
    ).split(",")
    if origin.strip()
]

# Maximum number of websocket clients kept by the in-process hub.
MAX_WEBSOCKET_CLIENTS = int(
    os.getenv(
        "P308_MAX_WEBSOCKET_CLIENTS",
        "100",
    )
)
