from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import paho.mqtt.client as mqtt

from api.live_state import api_live_state
from api.websocket_manager import (
    websocket_manager,
)
from config.mqtt_config import (
    ALERT_TOPIC,
    BROKER_HOST,
    BROKER_PORT,
    CONTROL_TOPIC,
    DECISION_TOPIC,
    EVENT_TOPIC,
    OPERATOR_SUMMARY_TOPIC,
    TELEMETRY_TOPIC,
)
from core.logging_config import (
    get_logger,
)
from core.metrics import (
    MQTT_CONNECTED,
    observe_mqtt_payload,
)


logger = get_logger(
    __name__
)


TOPIC_CHANNEL_MAP = {
    TELEMETRY_TOPIC: "telemetry",
    DECISION_TOPIC: "decision",
    CONTROL_TOPIC: "control",
    ALERT_TOPIC: "alert",
    EVENT_TOPIC: "event",
    OPERATOR_SUMMARY_TOPIC: (
        "operator_summary"
    ),
}


class MQTTAPIBridge:

    def __init__(self) -> None:

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=(
                "p308-fastapi-bridge"
            ),
        )

        self.client.on_connect = (
            self.on_connect
        )
        self.client.on_disconnect = (
            self.on_disconnect
        )
        self.client.on_message = (
            self.on_message
        )

        self.client.reconnect_delay_set(
            min_delay=1,
            max_delay=30,
        )

        self._event_loop: (
            asyncio.AbstractEventLoop | None
        ) = None

        self._connected = False
        self._last_error: str | None = None
        self._last_message_at: str | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def last_message_at(self) -> str | None:
        return self._last_message_at

    def start(
        self,
        event_loop: asyncio.AbstractEventLoop,
    ) -> None:

        self._event_loop = (
            event_loop
        )

        logger.info(
            "Starting MQTT API bridge"
        )

        self.client.connect_async(
            BROKER_HOST,
            BROKER_PORT,
            keepalive=60,
        )

        self.client.loop_start()

    def stop(self) -> None:

        logger.info(
            "Stopping MQTT API bridge"
        )

        try:
            self.client.disconnect()
        finally:
            self.client.loop_stop()

    def on_connect(
        self,
        client,
        userdata,
        flags,
        reason_code,
        properties,
    ) -> None:

        if reason_code == 0:

            self._connected = True
            self._last_error = None
            MQTT_CONNECTED.set(
                1
            )

            for topic in (
                TOPIC_CHANNEL_MAP
            ):
                client.subscribe(
                    topic,
                    qos=1,
                )

            logger.info(
                "FastAPI MQTT bridge connected to %s:%s",
                BROKER_HOST,
                BROKER_PORT,
            )

        else:
            self._connected = False
            MQTT_CONNECTED.set(
                0
            )
            self._last_error = (
                f"MQTT connection failed: "
                f"{reason_code}"
            )

            logger.error(
                self._last_error
            )

    def on_disconnect(
        self,
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties,
    ) -> None:

        self._connected = False
        MQTT_CONNECTED.set(
            0
        )

        if reason_code != 0:
            self._last_error = (
                f"MQTT disconnected: "
                f"{reason_code}"
            )

            logger.warning(
                self._last_error
            )

    def on_message(
        self,
        client,
        userdata,
        message,
    ) -> None:

        channel = (
            TOPIC_CHANNEL_MAP.get(
                message.topic
            )
        )

        if channel is None:
            return

        parse_error = False

        try:
            raw = (
                message.payload.decode(
                    "utf-8"
                )
            )

            payload: Any = (
                json.loads(
                    raw
                )
            )

        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):

            parse_error = True

            payload = {
                "raw": (
                    message.payload.decode(
                        "utf-8",
                        errors="replace",
                    )
                ),
                "parse_error": True,
            }

            logger.warning(
                "MQTT payload parse error on channel=%s topic=%s",
                channel,
                message.topic,
            )

        received_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        self._last_message_at = (
            received_at
        )

        api_live_state.update(
            channel=channel,
            payload=payload,
        )

        observe_mqtt_payload(
            channel=channel,
            payload=payload,
            parse_error=parse_error,
        )

        websocket_message = {
            "type": channel,
            "topic": message.topic,
            "received_at": received_at,
            "payload": payload,
        }

        if (
            self._event_loop
            is not None
            and not self._event_loop.is_closed()
        ):
            try:
                asyncio.run_coroutine_threadsafe(
                    websocket_manager.broadcast(
                        websocket_message
                    ),
                    self._event_loop,
                )
            except RuntimeError:
                logger.exception(
                    "Failed to schedule websocket broadcast"
                )


mqtt_api_bridge = MQTTAPIBridge()
