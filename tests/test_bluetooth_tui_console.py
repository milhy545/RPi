import asyncio
import sys
from itertools import pairwise
from pathlib import Path

from rich.text import Text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rpi_dashboard.tui.bluetooth_console import (
    adapter_slots,
    build_bluetooth_console,
    classify_device,
)


def bluetooth_state(adapter_count: int = 2) -> dict:
    adapters = [
        {
            "id": "adapter-a",
            "index": 0,
            "address": "B8:27:EB:12:34:56",
            "alias": "Internal Bluetooth",
            "present": True,
            "powered": True,
            "pairable": True,
            "discoverable": True,
        },
        {
            "id": "adapter-b",
            "index": 1,
            "address": "00:1A:7D:65:43:21",
            "alias": "USB Bluetooth",
            "present": True,
            "powered": True,
            "pairable": True,
            "discoverable": False,
        },
    ][:adapter_count]
    devices = []
    if adapter_count:
        devices.extend(
            [
                {
                    "key": "adapter-a/soundbar",
                    "adapter_id": "adapter-a",
                    "address": "24:4B:03:92:0B:8C",
                    "name": "[Samsung] Soundbar",
                    "kind": "speaker",
                    "rssi": -48,
                    "paired": True,
                    "connected": True,
                    "present": True,
                },
                {
                    "key": "adapter-a/phone",
                    "adapter_id": "adapter-a",
                    "address": "11:22:33:44:55:66",
                    "name": "Smartphone XYZ",
                    "kind": "phone",
                    "rssi": -82,
                    "paired": False,
                    "connected": False,
                    "present": True,
                },
            ]
        )
    if adapter_count > 1:
        devices.extend(
            [
                {
                    "key": "adapter-b/xbox",
                    "adapter_id": "adapter-b",
                    "address": "5C:BA:37:01:74:E9",
                    "name": "Xbox Wireless Controller",
                    "kind": "xbox_controller",
                    "rssi": -40,
                    "paired": True,
                    "connected": True,
                    "present": True,
                },
                {
                    "key": "adapter-b/sensor",
                    "adapter_id": "adapter-b",
                    "address": "AA:BB:CC:DD:EE:FF",
                    "name": "BLE Sensor",
                    "kind": "sensor",
                    "rssi": -84,
                    "paired": False,
                    "connected": False,
                    "present": True,
                },
            ]
        )
    return {
        "schema_version": 2,
        "backend": {"name": "bluez-dbus", "available": True, "degraded": False},
        "adapters": adapters,
        "devices": devices,
        "settings": {"auto_connect": True},
        "operations": [
            {
                "type": "connect",
                "state": "succeeded",
                "updated_at": "2026-07-21T20:22:31+00:00",
            }
        ],
        "events": [
            {
                "type": "device_connected",
                "message": "Adapter B: Connected - Xbox Controller",
                "timestamp": "2026-07-21T20:22:28+00:00",
            }
        ],
    }


def plain(markup: str) -> str:
    return Text.from_markup(markup).plain


def test_adapter_slots_are_stable_by_bluez_index() -> None:
    state = bluetooth_state()
    adapter_a, adapter_b = adapter_slots(list(reversed(state["adapters"])))

    assert adapter_a["id"] == "adapter-a"
    assert adapter_b["id"] == "adapter-b"


def test_device_classification_covers_reference_groups() -> None:
    assert classify_device({"kind": "speaker"}) == "audio_output"
    assert classify_device({"icon": "audio-headset", "name": "Wireless Headphones"}) == "audio_output"
    assert classify_device({"name": "Alexa Echo Dot"}) == "audio_input"
    assert classify_device({"name": "BLE Sensor"}) == "io"
    assert classify_device({"icon": "input-gaming"}) == "controller"


def test_full_console_contains_every_reference_panel() -> None:
    state = bluetooth_state()
    state["selected_device_key"] = "adapter-a/soundbar"
    view = build_bluetooth_console(
        state,
        facts={"os": "Bookworm (64-bit)", "kernel": "6.6.31", "bluez": "5.72", "uptime": "3d 14h"},
        cpu_percent=18,
        memory_percent=23,
    )

    assert "RPi Bluetooth Control Center (TUI)" in plain(view.header)
    assert "(Samsung)" in plain(view.adapter_a)
    assert ">1 (Samsung)" in plain(view.adapter_a)
    assert "Target: (Samsung) Soundbar" in plain(view.footer)
    assert "AUDIO OUTPUT DEVICES" in plain(view.topology)
    assert "AUDIO INPUT DEVICES" in plain(view.topology)
    assert "IO DEVICES" in plain(view.topology)
    assert "CONTROLLERS & IO DEVICES" in plain(view.topology)
    assert "Strong (> -70 dBm)" in plain(view.legend)
    assert "ADAPTER A DEVICES (AUDIO)" in plain(view.adapter_a)
    assert "ADAPTER B DEVICES (IO & CONTROLLERS)" in plain(view.adapter_b)
    assert "AVAILABLE DEVICES" in plain(view.available)
    assert "QUICK ACTIONS" in plain(view.actions)
    assert "ADAPTER STATUS" in plain(view.adapter_status)
    assert "DIAGNOSTICS" in plain(view.diagnostics)
    assert "RECENT EVENTS" in plain(view.recent_events)
    assert "HELP" in plain(view.help)
    assert "RPI OS: Bookworm (64-bit)" in plain(view.footer)
    assert "CPU: 18%" in plain(view.footer)
    assert "Mem: 23%" in plain(view.footer)


def test_zero_and_one_adapter_states_are_honest_and_ascii_safe() -> None:
    for count in (0, 1):
        view = build_bluetooth_console(bluetooth_state(count))
        rendered = "\n".join(plain(value) for value in view.__dict__.values())
        rendered.encode("ascii")
        assert "Not Present" in rendered
        assert "-- dBm" in rendered
        if count:
            assert "Powered On" in rendered
        else:
            assert "Adapter Address: --" in rendered


def test_live_textual_layout_switches_at_supported_sizes(monkeypatch) -> None:
    async def run_check() -> None:
        import tui
        from textual.widgets import Static, TabbedContent

        state = bluetooth_state()
        monkeypatch.setattr(
            tui.devices_service,
            "devices_state",
            lambda: {"ok": True, "bluetooth": {"v2": state, "devices": state["devices"]}},
        )
        tui.API_PORT = 0

        full_app = tui.RPiDashboard()
        async with full_app.run_test(size=(170, 48)) as pilot:
            full_app.query_one(TabbedContent).active = "tab_bluetooth"
            await full_app.update_bluetooth_devices()
            await pilot.pause(0.1)
            panel = full_app.query_one("#panel_bluetooth")
            assert not panel.has_class("bt-compact")
            assert full_app.query_one("#txt_bt_legend").region.height == 3
            assert full_app.query_one("#bt_terminal_middle").size.height == 11
            assert full_app.query_one("#bt_terminal_bottom").size.height == 11
            for row in (
                (
                    "#txt_bluetooth_adapter_a",
                    "#txt_bluetooth_adapter_b",
                    "#txt_bluetooth_available",
                    "#txt_bluetooth_actions",
                ),
                ("#txt_bt_adapter_status", "#txt_bt_diagnostics", "#txt_bt_events", "#txt_bt_help"),
            ):
                regions = [full_app.query_one(selector).region for selector in row]
                assert all(left.right <= right.x for left, right in pairwise(regions))
            assert "TOPOLOGY" in str(full_app.query_one("#txt_bluetooth_topology", Static).render())
            assert "DIAGNOSTICS" in str(full_app.query_one("#txt_bt_diagnostics", Static).render())
            assert "Bluetooth Service" in str(full_app.query_one("#txt_bt_footer", Static).render())
            assert full_app._bt_selected_device_key == "adapter-a/soundbar"
            await pilot.press("down")
            await pilot.pause(0.05)
            assert full_app._bt_selected_device_key == "adapter-a/phone"
            assert "Smartphone XYZ" in str(full_app.query_one("#txt_bt_footer", Static).render())

        compact_app = tui.RPiDashboard()
        async with compact_app.run_test(size=(85, 24)) as pilot:
            compact_app.query_one(TabbedContent).active = "tab_bluetooth"
            await compact_app.update_bluetooth_devices()
            await pilot.pause(0.1)
            panel = compact_app.query_one("#panel_bluetooth")
            assert panel.has_class("bt-compact")
            compact = str(compact_app.query_one("#txt_bt_compact", Static).render())
            assert "RPi Bluetooth Control Center" in compact
            assert "(Samsung) Soundbar" in compact
            assert "Smartphone XYZ" in compact
            compact_widget = compact_app.query_one("#txt_bt_compact", Static)
            assert compact_widget.content_size.height == compact_widget.size.height
            assert "[M] Settings" in compact
            assert "Settings" in compact_app.export_screenshot()

    asyncio.run(run_check())


def test_bluetooth_keyboard_actions_and_visible_placeholders(monkeypatch) -> None:
    async def run_check() -> None:
        import tui
        from textual.widgets import Static, TabbedContent

        calls = []
        state = bluetooth_state()
        monkeypatch.setattr(
            tui.devices_service,
            "devices_state",
            lambda: {"ok": True, "bluetooth": {"v2": state, "devices": state["devices"]}},
        )
        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(170, 48)) as pilot:
            app.query_one(TabbedContent).active = "tab_bluetooth"
            await app.update_bluetooth_devices()

            async def fake_action(action: str) -> None:
                calls.append(action)

            async def fake_scan() -> None:
                calls.append("scan")

            async def fake_refresh() -> None:
                calls.append("refresh")

            monkeypatch.setattr(app, "run_bluetooth_action", fake_action)
            monkeypatch.setattr(app, "scan_bluetooth", fake_scan)
            monkeypatch.setattr(app, "update_bluetooth_devices", fake_refresh)
            await pilot.press("s", "p", "c", "d", "x", "r")
            await pilot.pause(0.1)

            assert calls == ["scan", "pair", "connect", "disconnect", "remove", "refresh"]
            await pilot.press("g")
            await pilot.pause(0.05)
            footer = str(app.query_one("#txt_bt_footer", Static).render())
            assert "Adapter priority is planned" in footer
            await pilot.press("m")
            await pilot.pause(0.05)
            footer = str(app.query_one("#txt_bt_footer", Static).render())
            assert "More settings are available" in footer

    asyncio.run(run_check())
