"""
MQTT gate publisher used by backend access decisions.
"""
from __future__ import annotations

import logging
import json
import threading
import time
import uuid
from typing import Any, Callable, Dict, Optional

import paho.mqtt.client as mqtt

from app.config import settings
from app.utils.timezone import iso_local

logger = logging.getLogger(__name__)


class GateMQTTPublisher:
    """Small persistent MQTT publisher for gate commands."""

    def __init__(self) -> None:
        self.broker = settings.MQTT_BROKER
        self.port = settings.MQTT_PORT
        self.keepalive = settings.MQTT_KEEPALIVE
        self.topic_gate = settings.MQTT_TOPIC_GATE
        self.topic_gate_ack = settings.MQTT_TOPIC_GATE_ACK
        self.topic_parking_status = settings.MQTT_TOPIC_PARKING_STATUS
        self.client_id = settings.BACKEND_MQTT_CLIENT_ID
        self.qos = settings.MQTT_QOS

        self._client: Optional[mqtt.Client] = None
        self._connected = threading.Event()
        self._lock = threading.Lock()
        self._ack_lock = threading.Lock()
        self._loop_started = False
        self._ack_handler: Optional[Callable[[Dict[str, Any]], None]] = None
        self._acks_by_command_id: Dict[str, Dict[str, Any]] = {}

    def _build_client(self) -> mqtt.Client:
        client = mqtt.Client(client_id=self.client_id, clean_session=True)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        client.reconnect_delay_set(min_delay=1, max_delay=15)
        return client

    def _on_connect(self, client: mqtt.Client, userdata, flags, rc: int) -> None:
        del userdata, flags
        if rc == 0:
            self._connected.set()
            logger.info("[MQTT] Backend connected broker=%s:%s", self.broker, self.port)
            subscribe_rc, _mid = client.subscribe(self.topic_gate_ack, qos=self.qos)
            if subscribe_rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info("[MQTT] Backend subscribed gate ACK topic=%s", self.topic_gate_ack)
            else:
                logger.error(
                    "[MQTT] Backend subscribe gate ACK failed rc=%s topic=%s",
                    subscribe_rc,
                    self.topic_gate_ack,
                )
        else:
            self._connected.clear()
            logger.error("[MQTT] Backend connection failed rc=%s", rc)

    def _on_disconnect(self, client: mqtt.Client, userdata, rc: int) -> None:
        del client, userdata
        self._connected.clear()
        if rc != 0:
            logger.warning("[MQTT] Backend unexpected disconnect rc=%s", rc)

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        del client, userdata
        if msg.topic != self.topic_gate_ack:
            return

        try:
            payload_text = msg.payload.decode("utf-8").strip()
            ack = json.loads(payload_text)
            if not isinstance(ack, dict):
                logger.warning("[MQTT] Ignored gate ACK payload that is not an object: %s", payload_text)
                return
        except Exception as exc:
            logger.warning("[MQTT] Invalid gate ACK payload topic=%s error=%s", msg.topic, exc)
            return

        command_id = str(ack.get("command_id") or "").strip()
        if not command_id:
            logger.warning("[MQTT] Gate ACK missing command_id: %s", ack)
            return

        ack.setdefault("received_at", iso_local())
        with self._ack_lock:
            self._acks_by_command_id[command_id] = dict(ack)
            while len(self._acks_by_command_id) > 500:
                self._acks_by_command_id.pop(next(iter(self._acks_by_command_id)), None)

        logger.info(
            "[GATE] ACK received command_id=%s status=%s device=%s",
            command_id,
            ack.get("status"),
            ack.get("device_id"),
        )

        if self._ack_handler:
            try:
                self._ack_handler(dict(ack))
            except Exception as exc:
                logger.warning("[GATE] ACK handler failed command_id=%s error=%s", command_id, exc)

    def set_ack_handler(self, handler: Optional[Callable[[Dict[str, Any]], None]]) -> None:
        self._ack_handler = handler

    def get_ack(self, command_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not command_id:
            return None
        with self._ack_lock:
            ack = self._acks_by_command_id.get(command_id)
            return dict(ack) if ack else None

    def ensure_connected(self, timeout: float = 3.0) -> bool:
        with self._lock:
            if self._client is not None and self._connected.is_set():
                return True

            if self._client is None:
                self._client = self._build_client()

            try:
                self._client.connect(self.broker, self.port, self.keepalive)
                if not self._loop_started:
                    self._client.loop_start()
                    self._loop_started = True
            except Exception as exc:
                logger.error("[MQTT] Backend connect failed: %s", exc)
                self._connected.clear()
                return False

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._connected.is_set():
                return True
            time.sleep(0.02)

        logger.error("[MQTT] Backend connect timeout broker=%s:%s", self.broker, self.port)
        return False

    def publish_open(
        self,
        *,
        command_id: Optional[str] = None,
        event_id: Optional[str] = None,
        session_id: Optional[str] = None,
        action: Optional[str] = None,
        gate_id: Optional[int] = None,
        timeout: float = 3.0,
    ) -> Dict[str, Any]:
        command_id = command_id or uuid.uuid4().hex
        result: Dict[str, Any] = {
            "success": False,
            "command_id": command_id,
            "topic": self.topic_gate,
        }

        if not self.ensure_connected(timeout=timeout):
            result["reason"] = "mqtt_not_connected"
            return result

        assert self._client is not None
        payload = {
            "schema": "smartparking.gate_command.v1",
            "command": "OPEN",
            "command_id": command_id,
            "gate_id": gate_id,
            "event_id": event_id,
            "session_id": session_id,
            "action": action,
            "issued_at": iso_local(),
        }
        payload_text = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        try:
            info = self._client.publish(self.topic_gate, payload_text, qos=self.qos, retain=False)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error("[MQTT] Publish OPEN failed rc=%s topic=%s", info.rc, self.topic_gate)
                result["reason"] = f"publish_rc_{info.rc}"
                return result

            info.wait_for_publish(timeout=timeout)
            if not info.is_published():
                logger.error("[MQTT] Publish OPEN timed out topic=%s", self.topic_gate)
                result["reason"] = "publish_timeout"
                return result

            logger.info("[GATE] OPEN command sent command_id=%s topic=%s", command_id, self.topic_gate)
            result["success"] = True
            result["payload"] = payload
            return result
        except Exception as exc:
            logger.error("[MQTT] Publish OPEN exception: %s", exc)
            self._connected.clear()
            result["reason"] = "publish_exception"
            result["error"] = str(exc)
            return result

    def publish_parking_status(self, status: Dict[str, Any], timeout: float = 3.0) -> bool:
        if not self.ensure_connected(timeout=timeout):
            return False

        assert self._client is not None
        payload = json.dumps(status, ensure_ascii=True, separators=(",", ":"))
        try:
            info = self._client.publish(
                self.topic_parking_status,
                payload,
                qos=self.qos,
                retain=True,
            )
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error(
                    "[MQTT] Publish parking status failed rc=%s topic=%s",
                    info.rc,
                    self.topic_parking_status,
                )
                return False

            info.wait_for_publish(timeout=timeout)
            if not info.is_published():
                logger.error("[MQTT] Publish parking status timed out topic=%s", self.topic_parking_status)
                return False

            logger.info(
                "[PARKING] Status sent topic=%s available=%s total=%s",
                self.topic_parking_status,
                status.get("available"),
                status.get("total"),
            )
            return True
        except Exception as exc:
            logger.error("[MQTT] Publish parking status exception: %s", exc)
            self._connected.clear()
            return False

    def close(self) -> None:
        with self._lock:
            if self._client is None:
                return
            try:
                if self._loop_started:
                    self._client.loop_stop()
                self._client.disconnect()
            except Exception as exc:
                logger.warning("[MQTT] Backend close error: %s", exc)
            finally:
                self._client = None
                self._loop_started = False
                self._connected.clear()


gate_mqtt_publisher = GateMQTTPublisher()
