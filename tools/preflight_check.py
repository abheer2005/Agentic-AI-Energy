from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from core.startup_checks import (
    has_failures,
    run_preflight,
)


def main() -> None:

    print(
        "\n============================================================"
    )
    print(
        "P_308 AGENTIC ENERGY AI - PREFLIGHT CHECK"
    )
    print(
        "============================================================\n"
    )

    results = run_preflight(
        include_services=True
    )

    for item in results:

        symbol = {
            "PASS": "✅",
            "WARN": "⚠️",
            "FAIL": "❌",
        }.get(
            item.status,
            "•",
        )

        print(
            f"{symbol} "
            f"{item.status:<4} "
            f"{item.name:<32} "
            f"{item.detail}"
        )

    pass_count = sum(
        item.status == "PASS"
        for item in results
    )

    warn_count = sum(
        item.status == "WARN"
        for item in results
    )

    fail_count = sum(
        item.status == "FAIL"
        for item in results
    )

    print(
        "\n------------------------------------------------------------"
    )
    print(
        f"PASS={pass_count}  "
        f"WARN={warn_count}  "
        f"FAIL={fail_count}"
    )

    if has_failures(
        results
    ):
        print(
            "\n❌ Preflight FAILED."
        )
        raise SystemExit(
            1
        )

    print(
        "\n✅ Preflight PASSED. "
        "Warnings may simply mean optional "
        "runtime services are not started yet."
    )


if __name__ == "__main__":
    main()
