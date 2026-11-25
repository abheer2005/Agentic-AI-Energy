from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket

from config.api_config import (
    MAX_WEBSOCKET_CLIENTS,
)


class WebSocketManager:
    """
    In-process websocket fan-out hub.

    Each connected dashboard receives the same normalized live event stream.
    """

    def __init__(self) -> None:
        self._clients: set[
            WebSocket
        ] = set()

        self._lock = asyncio.Lock()

    @property
    def client_count(self) -> int:
        return len(
            self._clients
        )

    async def connect(
        self,
        websocket: WebSocket,
    ) -> bool:

        async with self._lock:

            if (
                len(self._clients)
                >= MAX_WEBSOCKET_CLIENTS
            ):
                await websocket.close(
                    code=1013,
                    reason=(
                        "WebSocket capacity reached"
                    ),
                )
                return False

            await websocket.accept()

            self._clients.add(
                websocket
            )

        return True

    async def disconnect(
        self,
        websocket: WebSocket,
    ) -> None:

        async with self._lock:
            self._clients.discard(
                websocket
            )

    async def broadcast(
        self,
        message: dict[str, Any],
    ) -> None:

        if not self._clients:
            return

        async with self._lock:
            clients = list(
                self._clients
            )

        dead: list[
            WebSocket
        ] = []

        for websocket in clients:
            try:
                await websocket.send_json(
                    message
                )
            except Exception:
                dead.append(
                    websocket
                )

        if dead:
            async with self._lock:
                for websocket in dead:
                    self._clients.discard(
                        websocket
                    )


websocket_manager = WebSocketManager()
