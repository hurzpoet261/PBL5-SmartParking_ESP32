"""
MQTT gate publisher used by backend access decisions.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class GateMQTTPublisher:
    """Small persistent MQTT publisher for gate commands."""

    def __init__(self) -> None:
        self.broker = os.getenv("MQTT_BROKER", "broker.hivemq.com")
        self.port = int(os.getenv("MQTT_PORT", "1883"))
        self.keepalive = int(os.getenv("MQTT_KEEPALIVE", "60"))
        self.topic_gate = os.getenv("MQTT_TOPIC_GATE", "pbl5/smartparking/gate")
        self.client_id = os.getenv("BACKEND_MQTT_CLIENT_ID", "SmartParkingBackendGate")
        self.qos = int(os.getenv("MQTT_QOS", "1"))

        self._client: Optional[mqtt.Client] = None
        self._connected = threading.Event()
        self._lock = threading.Lock()
        self._loop_started = False

    def _build_client(self) -> mqtt.Client:
        client = mqtt.Client(client_id=self.client_id, clean_session=True)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.reconnect_delay_set(min_delay=1, max_delay=15)
        return client

    def _on_connect(self, client: mqtt.Client, userdata, flags, rc: int) -> None:
        del client, userdata, flags
        if rc == 0:
            self._connected.set()
            logger.info("[MQTT] Backend connected broker=%s:%s", self.broker, self.port)
        else:
            self._connected.clear()
            logger.error("[MQTT] Backend connection failed rc=%s", rc)

    def _on_disconnect(self, client: mqtt.Client, userdata, rc: int) -> None:
        del client, userdata
        self._connected.clear()
        if rc != 0:
            logger.warning("[MQTT] Backend unexpected disconnect rc=%s", rc)

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

    def publish_open(self, timeout: float = 3.0) -> bool:
        if not self.ensure_connected(timeout=timeout):
            return False

        assert self._client is not None
        try:
            info = self._client.publish(self.topic_gate, "OPEN", qos=self.qos, retain=False)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error("[MQTT] Publish OPEN failed rc=%s topic=%s", info.rc, self.topic_gate)
                return False

            info.wait_for_publish(timeout=timeout)
            if not info.is_published():
                logger.error("[MQTT] Publish OPEN timed out topic=%s", self.topic_gate)
                return False
            logger.info("[GATE] OPEN command sent topic=%s", self.topic_gate)
            return True
        except Exception as exc:
            logger.error("[MQTT] Publish OPEN exception: %s", exc)
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
