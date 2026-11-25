from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any, Optional


class EnergyStateManager:
    """
    Thread-safe shared state store for the latest
    validated energy telemetry.

    Future AI agents will read data from this manager.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._latest_state: Optional[dict[str, Any]] = None
        self._total_updates = 0

    def update(self, telemetry: dict[str, Any]) -> None:
        """
        Store the latest validated telemetry.
        """

        with self._lock:
            self._latest_state = deepcopy(telemetry)
            self._total_updates += 1

    def get_latest(self) -> Optional[dict[str, Any]]:
        """
        Return a safe copy of the current state.
        """

        with self._lock:

            if self._latest_state is None:
                return None

            return deepcopy(self._latest_state)

    def get_value(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Read one telemetry field safely.
        """

        with self._lock:

            if self._latest_state is None:
                return default

            return self._latest_state.get(
                key,
                default
            )

    @property
    def total_updates(self) -> int:
        with self._lock:
            return self._total_updates


# Single shared state instance used across the application.
energy_state = EnergyStateManager()