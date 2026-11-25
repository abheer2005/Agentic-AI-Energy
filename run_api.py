from __future__ import annotations

import sys
from pathlib import Path

import uvicorn


PROJECT_ROOT = Path(
    __file__
).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from config.api_config import (
    API_HOST,
    API_PORT,
)
from core.startup_checks import (
    has_failures,
    run_preflight,
)


def print_preflight() -> bool:

    print(
        "\n🔎 Running P_308 API preflight..."
    )

    results = run_preflight(
        include_services=False
    )

    for item in results:

        symbol = (
            "✅"
            if item.status == "PASS"
            else "❌"
        )

        print(
            f"{symbol} {item.name}: "
            f"{item.detail}"
        )

    return not has_failures(
        results
    )


if __name__ == "__main__":

    if not print_preflight():

        print(
            "\n❌ Preflight failed. "
            "Fix missing dependencies/files "
            "before starting the API."
        )

        raise SystemExit(
            1
        )

    print(
        f"\n🚀 Starting API at "
        f"http://{API_HOST}:{API_PORT}"
    )

    uvicorn.run(
        "api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info",
    )
