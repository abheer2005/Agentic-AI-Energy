from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any


class APILiveState:
    """
    Thread-safe latest-value store fed by MQTT.

    MQTT callbacks run in a Paho background thread, while FastAPI endpoints
    run in the async server thread. A lock keeps cross-thread reads safe.
    """

    def __init__(self) -> None:
        self._lock = Lock()

        self._data: dict[str, Any] = {
            "telemetry": None,
            "decision": None,
            "control": None,
            "alert": None,
            "event": None,
            "operator_summary": None,
        }

        self._updated_at: dict[str, str | None] = {
            key: None
            for key in self._data
        }

        self._message_count = 0

    def update(
        self,
        channel: str,
        payload: Any,
    ) -> None:

        if channel not in self._data:
            return

        now = datetime.now(
            timezone.utc
        ).isoformat()

        with self._lock:
            self._data[channel] = deepcopy(
                payload
            )
            self._updated_at[channel] = now
            self._message_count += 1

    def get(
        self,
        channel: str,
    ) -> Any:

        with self._lock:
            return deepcopy(
                self._data.get(
                    channel
                )
            )

    def snapshot(self) -> dict[str, Any]:

        with self._lock:
            return {
                "data": deepcopy(
                    self._data
                ),
                "updated_at": deepcopy(
                    self._updated_at
                ),
                "message_count": (
                    self._message_count
                ),
            }


api_live_state = APILiveState()
