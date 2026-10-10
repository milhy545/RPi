"""Smart Home Service (MQTT Bridge & Home Assistant Integration)."""

import json
import os
import threading
from typing import Any, Callable, Dict, Optional

mqtt: Any = None

try:
    import paho.mqtt.client as _mqtt_mod
    mqtt = _mqtt_mod
except ImportError:
    pass


class MQTTBridge:
    """Lightweight MQTT bridge for Home Assistant real-time telemetry."""

    def __init__(self, broker_url: Optional[str] = None):
        self.broker_url = broker_url or os.environ.get("MQTT_BROKER_URL", "192.168.0.58")
        self.port = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
        self.client: Optional[Any] = None
        self._connected = False
        self._lock = threading.Lock()

    def connect(self) -> bool:
        if not mqtt:
            return False
        try:
            with self._lock:
                if self._connected:
                    return True
                self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
                self.client.on_connect = self._on_connect
                self.client.on_disconnect = self._on_disconnect
                self.client.connect_async(self.broker_url, self.port, 60)
                self.client.loop_start()
                self._connected = True
                return True
        except Exception:
            self._connected = False
            return False

    def disconnect(self) -> None:
        with self._lock:
            if self.client and self._connected:
                self.client.loop_stop()
                self.client.disconnect()
                self._connected = False

    def publish_status(self, topic: str, payload: Dict[str, Any]) -> bool:
        if not self._connected or not self.client:
            return False
        try:
            full_topic = f"rpi-tv/{topic}"
            self.client.publish(full_topic, json.dumps(payload), qos=0)
            return True
        except Exception:
            return False

    def subscribe_commands(self, topic: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        if not self._connected or not self.client:
            return False
        try:
            full_topic = f"rpi-tv/{topic}/command"
            self.client.subscribe(full_topic)

            def _on_message(client, userdata, msg):
                try:
                    data = json.loads(msg.payload.decode("utf-8"))
                    callback(data)
                except Exception:
                    pass

            self.client.message_callback_add(full_topic, _on_message)
            return True
        except Exception:
            return False

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        pass

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        with self._lock:
            self._connected = False
