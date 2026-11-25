from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from config.alert_config import EVENT_DATABASE_NAME
from core.event_store import SQLiteEventStore


DATABASE = (
    PROJECT_ROOT
    / "data"
    / EVENT_DATABASE_NAME
)


def print_rows(
    title: str,
    rows: list[dict],
) -> None:

    print(
        "\n"
        + "=" * 90
    )
    print(title)
    print("=" * 90)

    if not rows:
        print("No records found.")
        return

    for row in rows:
        payload = (
            row.get(
                "payload_json",
                {}
            )
        )

        print(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
            )
        )
        print("-" * 90)


def main() -> None:

    store = SQLiteEventStore(
        DATABASE
    )

    print(
        f"\n🗄️ Database: {DATABASE}"
    )

    counts = store.counts()

    print(
        f"Alerts: {counts['alerts']} | "
        f"Events: {counts['events']}"
    )

    print_rows(
        "LATEST ALERTS",
        store.latest_alerts(
            limit=10
        ),
    )

    print_rows(
        "LATEST EVENTS",
        store.latest_events(
            limit=20
        ),
    )


if __name__ == "__main__":
    main()
