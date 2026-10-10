"""Behavior tests for the MQTT smart-home bridge."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from rpi_dashboard.services import smart_home


def test_bridge_connect_publish_subscribe_and_disconnect(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    mqtt = SimpleNamespace(
        Client=MagicMock(return_value=client),
        CallbackAPIVersion=SimpleNamespace(VERSION2=2),
    )
    monkeypatch.setattr(smart_home, "mqtt", mqtt)
    bridge = smart_home.MQTTBridge("broker.local")

    assert bridge.connect() is True
    assert bridge.connect() is True
    mqtt.Client.assert_called_once_with(2)
    client.connect_async.assert_called_once_with("broker.local", bridge.port, 60)
    client.loop_start.assert_called_once_with()

    assert bridge.publish_status("status", {"playing": True}) is True
    client.publish.assert_called_once_with(
        "rpi-tv/status",
        json.dumps({"playing": True}),
        qos=0,
    )

    callback = MagicMock()
    assert bridge.subscribe_commands("player", callback) is True
    client.subscribe.assert_called_once_with("rpi-tv/player/command")
    on_message = client.message_callback_add.call_args.args[1]
    on_message(None, None, SimpleNamespace(payload=b'{"action":"stop"}'))
    callback.assert_called_once_with({"action": "stop"})

    bridge.disconnect()
    client.loop_stop.assert_called_once_with()
    client.disconnect.assert_called_once_with()
    assert bridge._connected is False


def test_bridge_degrades_when_mqtt_is_missing_or_client_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smart_home, "mqtt", None)
    bridge = smart_home.MQTTBridge()
    assert bridge.connect() is False
    assert bridge.publish_status("status", {}) is False
    assert bridge.subscribe_commands("player", MagicMock()) is False

    failing_mqtt = SimpleNamespace(
        Client=MagicMock(side_effect=RuntimeError("broker unavailable")),
        CallbackAPIVersion=SimpleNamespace(VERSION2=2),
    )
    monkeypatch.setattr(smart_home, "mqtt", failing_mqtt)
    assert bridge.connect() is False
    assert bridge._connected is False


def test_bridge_handles_publish_subscribe_and_callback_errors() -> None:
    bridge = smart_home.MQTTBridge()
    bridge._connected = True
    bridge.client = MagicMock()
    bridge.client.publish.side_effect = RuntimeError("offline")
    bridge.client.subscribe.side_effect = RuntimeError("offline")

    assert bridge.publish_status("status", {}) is False
    assert bridge.subscribe_commands("player", MagicMock()) is False

    bridge.client.subscribe.side_effect = None
    callback = MagicMock()
    assert bridge.subscribe_commands("player", callback) is True
    on_message = bridge.client.message_callback_add.call_args.args[1]
    on_message(None, None, SimpleNamespace(payload=b"not-json"))
    callback.assert_not_called()


def test_disconnect_callback_clears_connected_state() -> None:
    bridge = smart_home.MQTTBridge()
    bridge._connected = True
    bridge._on_disconnect(None, None, None, None)
    assert bridge._connected is False
