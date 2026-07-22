"""Pure rendering model for the Bluetooth terminal control center."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from rich.markup import escape


Device = dict[str, Any]
Adapter = dict[str, Any]


@dataclass(frozen=True)
class BluetoothConsoleView:
    header: str
    topology: str
    legend: str
    adapter_a: str
    adapter_b: str
    available: str
    actions: str
    adapter_status: str
    diagnostics: str
    recent_events: str
    help: str
    footer: str
    compact: str


def adapter_slots(adapters: list[Adapter]) -> tuple[Adapter, Adapter]:
    """Return deterministic Adapter A/B slots independent of list ordering."""
    ordered = sorted(
        adapters,
        key=lambda adapter: (
            adapter.get("index") is None,
            adapter.get("index", 999),
            str(adapter.get("id", "")),
        ),
    )
    return (ordered[0] if ordered else {}, ordered[1] if len(ordered) > 1 else {})


def classify_device(device: Device) -> str:
    """Map backend device evidence into one topology category."""
    kind = str(device.get("kind") or device.get("type") or "").lower()
    name = str(device.get("name") or device.get("alias") or "").lower()
    icon = str(device.get("icon") or "").lower()
    evidence = " ".join(str(item).lower() for item in device.get("kind_evidence") or [])
    combined = " ".join((kind, name, icon, evidence))
    if any(token in combined for token in ("gamepad", "xbox", "controller", "keyboard", "mouse", "midi", "input-gaming")):
        return "controller"
    if any(token in combined for token in ("speaker", "soundbar", "headphone", "headset", "audio-headset", "audio-output")):
        return "audio_output"
    if any(token in combined for token in ("microphone", "smartphone", "phone", "echo", "audio-input", "audio-source")):
        return "audio_input"
    return "io"


def _name(device: Device, width: int = 21) -> str:
    value = str(device.get("name") or device.get("alias") or "Unknown Device")
    value = value.replace("[", "(").replace("]", ")")
    return value.encode("ascii", errors="replace").decode("ascii")[:width]


def _rssi_value(device: Device) -> int | None:
    value = device.get("rssi")
    return int(value) if isinstance(value, int | float) else None


def _rssi(device: Device) -> str:
    value = _rssi_value(device)
    return f"{value} dBm" if value is not None else "-- dBm"


def _avg_rssi(devices: list[Device]) -> str:
    values = [value for device in devices if (value := _rssi_value(device)) is not None]
    return str(round(sum(values) / len(values))) if values else "--"


def _status(device: Device) -> tuple[str, str]:
    if device.get("connected"):
        return "Connected", "green"
    if device.get("paired"):
        return "Paired", "cyan"
    if device.get("present") is False:
        return "Absent", "red"
    return "Available", "yellow"


def _power(adapter: Adapter) -> tuple[str, str]:
    if not adapter:
        return "Not Present", "red"
    if adapter.get("powered"):
        return "Powered On", "green"
    return "Powered Off", "red"


def _adapter_devices(adapter: Adapter, devices: list[Device]) -> list[Device]:
    """Return devices assigned to a real adapter slot, never an empty placeholder."""
    adapter_id = adapter.get("id") if adapter else None
    if not adapter_id:
        return []
    return [device for device in devices if device.get("adapter_id") == adapter_id]


def _device_category_rows(devices: list[Device], category: str) -> list[str]:
    matching = [device for device in devices if classify_device(device) == category]
    rows = []
    for device in matching[:4]:
        rows.append(f"|-- {_name(device, 13):<13} {_rssi(device):>7}")
    placeholder = {
        "audio_output": "No audio outputs",
        "audio_input": "No audio inputs",
        "io": "No IO devices",
        "controller": "No controllers",
    }[category]
    if not rows:
        rows.append(f"|-- {placeholder}")
    while len(rows) < 4:
        rows.append("|-- --")
    return rows


def _topology_cell(value: str, color: str = "") -> str:
    cell = f"{value[:27]:<27}"
    return f"[{color}]{cell}[/]" if color else cell


def _topology(adapters: list[Adapter], devices: list[Device]) -> str:
    adapter_a, adapter_b = adapter_slots(adapters)
    devices_a = _adapter_devices(adapter_a, devices)
    devices_b = _adapter_devices(adapter_b, devices)
    categories = {
        name: _device_category_rows(devices, name)
        for name in ("audio_output", "audio_input", "io", "controller")
    }
    a_power, a_color = _power(adapter_a)
    b_power, b_color = _power(adapter_b)
    adapter_a_rows = [f"{a_power} RSSI {_avg_rssi(devices_a)}", "       /\\", "    --< BT >--", r"       \/"]
    adapter_b_rows = [f"{b_power} RSSI {_avg_rssi(devices_b)}", "       /\\", "    --< BT >--", r"       \/"]
    lines = [
        "[bold cyan]TOPOLOGY[/]",
        "".join(
            _topology_cell(title, color)
            for title, color in (
                ("AUDIO OUTPUT DEVICES", "bold cyan"),
                ("ADAPTER A / AUDIO", "bold cyan"),
                ("AUDIO INPUT DEVICES", "bold cyan"),
                ("IO DEVICES", "bold green"),
                ("ADAPTER B / IO", "bold green"),
                ("CONTROLLERS & IO DEVICES", "bold green"),
            )
        ),
    ]
    for index in range(4):
        lines.append(
            "".join(
                (
                    _topology_cell(categories["audio_output"][index], "cyan" if index == 0 else "dim"),
                    _topology_cell(adapter_a_rows[index], a_color),
                    _topology_cell(categories["audio_input"][index], "cyan" if index == 0 else "dim"),
                    _topology_cell(categories["io"][index], "green" if index == 0 else "dim"),
                    _topology_cell(adapter_b_rows[index], b_color),
                    _topology_cell(categories["controller"][index], "green" if index == 0 else "dim"),
                )
            )
        )
    lines.append(
        "".join(
            (
                _topology_cell(""),
                _topology_cell(
                    f"{len([d for d in devices_a if d.get('connected')])} Connected / "
                    f"{len([d for d in devices_a if not d.get('connected')])} Available",
                    "cyan",
                ),
                _topology_cell(""),
                _topology_cell(""),
                _topology_cell(
                    f"{len([d for d in devices_b if d.get('connected')])} Connected / "
                    f"{len([d for d in devices_b if not d.get('connected')])} Available",
                    "green",
                ),
                _topology_cell(""),
            )
        )
    )
    return "\n".join(lines)


def _adapter_table(title: str, adapter: Adapter, devices: list[Device], color: str, selected_key: str) -> str:
    rows = [f"[bold {color}]{title}[/]", " # Device         RSSI    Status", "--------------------------------------"]
    adapter_devices = _adapter_devices(adapter, devices)
    for index, device in enumerate(adapter_devices[:4], start=1):
        status, status_color = _status(device)
        marker = ">" if device.get("key") == selected_key else " "
        rows.append(f"{marker}{index} {_name(device, 12):<12} {_rssi(device):>7} [{status_color}]{status}[/]")
    while len(rows) < 7:
        rows.append("[dim]- --                   --      --[/]")
    rows.append(f"[{color}]Adapter Address:[/] {adapter.get('address', '--')}")
    return "\n".join(rows)


def _available(devices: list[Device], adapter_a: Adapter, adapter_b: Adapter, selected_key: str) -> str:
    labels = {
        adapter.get("id"): label
        for adapter, label in ((adapter_a, "A"), (adapter_b, "B"))
        if adapter.get("id")
    }
    rows = ["[bold yellow]AVAILABLE DEVICES[/]", "Device Name       RSSI    Adapter", "--------------------------------------"]
    available = [device for device in devices if not device.get("connected")]
    for device in available[:4]:
        marker = ">" if device.get("key") == selected_key else " "
        rows.append(f"{marker}{_name(device, 14):<14} {_rssi(device):>7} {labels.get(device.get('adapter_id'), '-')}")
    while len(rows) < 7:
        rows.append("[dim]--                   --      -[/]")
    rows.append(r"Press [yellow]\[P][/] to pair selected device")
    return "\n".join(rows)


def _adapter_status(adapters: list[Adapter], devices: list[Device]) -> str:
    rows = ["[bold cyan]ADAPTER STATUS[/]"]
    for label, adapter in zip(("A", "B"), adapter_slots(adapters), strict=True):
        adapter_devices = _adapter_devices(adapter, devices)
        power, color = _power(adapter)
        rows.extend(
            [
                f"Adapter {label}: [{color}]{power}[/]",
                f"  Connections: {len([d for d in adapter_devices if d.get('connected')])}  Available: {len([d for d in adapter_devices if not d.get('connected')])}",
                f"  RSSI (Avg): {_avg_rssi(adapter_devices)} dBm  TX Power: {adapter.get('tx_power', '--')} dBm",
            ]
        )
    return "\n".join(rows)


def _diagnostics(state: dict[str, Any], facts: dict[str, str]) -> str:
    adapters = state.get("adapters") or []
    backend = state.get("backend") or {}
    running = backend.get("available", True) and not backend.get("degraded")
    controllers = ", ".join(f"hci{adapter.get('index', '?')}" for adapter in adapters) or "none"
    return "\n".join(
        [
            "[bold cyan]DIAGNOSTICS[/]",
            f"Bluetooth Service: [{'green' if running else 'red'}]{'Running' if running else 'Degraded'}[/]",
            f"Host Controller: [green]{controllers}[/]",
            f"Discoverable: {'ON' if any(a.get('discoverable') for a in adapters) else 'OFF'}",
            f"Pairable: {'ON' if any(a.get('pairable') for a in adapters) else 'OFF'}",
            f"Uptime: {facts.get('uptime', '--')}",
            f"Kernel: {facts.get('kernel', '--')}",
            f"BlueZ: {facts.get('bluez', backend.get('name', '--'))}",
        ]
    )


def _events(state: dict[str, Any]) -> str:
    rows = ["[bold cyan]RECENT EVENTS[/]"]
    combined = []
    for operation in state.get("operations") or []:
        combined.append(
            (
                operation.get("updated_at") or operation.get("started_at") or "",
                f"{operation.get('type', 'operation')} - {operation.get('state', 'unknown')}",
                operation.get("state") == "failed",
            )
        )
    for event in state.get("events") or []:
        combined.append((event.get("timestamp") or "", event.get("message") or event.get("type") or "event", "failed" in str(event.get("type"))))
    for stamp, message, failed in sorted(combined, reverse=True)[:6]:
        try:
            time_text = datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).strftime("%H:%M:%S")
        except ValueError:
            time_text = "--:--:--"
        color = "red" if failed else "green"
        rows.append(f"{time_text} [{color}]{escape(str(message)[:43])}[/]")
    while len(rows) < 8:
        rows.append("[dim]--:--:-- No event[/]")
    return "\n".join(rows)


def build_bluetooth_console(
    state: dict[str, Any] | None,
    *,
    facts: dict[str, str] | None = None,
    cpu_percent: float | None = None,
    memory_percent: float | None = None,
) -> BluetoothConsoleView:
    """Build every visible Bluetooth TUI panel from one backend state snapshot."""
    state = state or {}
    facts = facts or {}
    adapters = list(state.get("adapters") or [])
    devices = list(state.get("devices") or [])
    adapter_a, adapter_b = adapter_slots(adapters)
    backend = state.get("backend") or {}
    connected = len([device for device in devices if device.get("connected")])
    paired = len([device for device in devices if device.get("paired")])
    auto_connect = (state.get("settings") or {}).get("auto_connect", True)
    selected_key = str(state.get("selected_device_key") or "")
    selected_device = next((device for device in devices if device.get("key") == selected_key), None)
    selected_name = _name(selected_device, 18) if selected_device else "None"
    service = "Degraded" if backend.get("degraded") or backend.get("available") is False else "Running"
    service_color = "red" if service == "Degraded" else "green"
    cpu = "--" if cpu_percent is None else f"{cpu_percent:.0f}%"
    memory = "--" if memory_percent is None else f"{memory_percent:.0f}%"
    header = (
        "[bold cyan](BT)[/] [bold]RPi Bluetooth Control Center (TUI)[/]  "
        "[cyan]Dual Adapter Management[/]                         "
        f"Auto Connect: [{'green' if auto_connect else 'red'}]{'ON' if auto_connect else 'OFF'}[/] | "
        r"\[S] Scan All  \[P] Pair New  \[T] Trust  \[R] Refresh  \[Q] Quit"
    )
    actions = "\n".join(
        [
            "[bold magenta]QUICK ACTIONS[/]",
            r"\[S] Scan All Adapters",
            r"\[P] Pair New Device",
            r"\[C] Connect to Device",
            r"\[D] Disconnect Device",
            r"\[R] Refresh Topology",
            r"\[X] Remove Paired Device",
            r"\[G] Adapter Priority",
            r"\[M] More Settings",
        ]
    )
    help_text = "\n".join(
        [
            "[bold cyan]HELP[/]",
            "Up/Down  Navigate",
            "Enter    Select Action",
            "Tab      Switch Panel",
            "T        Trust Device",
            "R        Refresh",
            "Q        Quit",
        ]
    )
    footer = (
        f"Bluetooth Service: [{service_color}]{service}[/]     Total Connected: [green]{connected}[/] | "
        f"Total Paired: [cyan]{paired}[/]     Target: [yellow]{selected_name}[/]     "
        f"RPI OS: {facts.get('os', '--')} | CPU: {cpu} | Mem: {memory}"
    )
    compact_rows = [
        f"[bold cyan](BT)[/] [bold]RPi Bluetooth Control Center[/] | Auto: {'ON' if auto_connect else 'OFF'}",
        f"Service [{service_color}]{service}[/] | Adapters {len(adapters)} | Connected {connected} | Paired {paired}",
        "[cyan]A / AUDIO[/] "
        + (f"{escape(str(adapter_a.get('alias') or adapter_a.get('id')))} {_power(adapter_a)[0]}" if adapter_a else "Not present"),
        "[green]B / IO[/]    "
        + (f"{escape(str(adapter_b.get('alias') or adapter_b.get('id')))} {_power(adapter_b)[0]}" if adapter_b else "Not present"),
    ]
    for device in devices[:2]:
        status, color = _status(device)
        marker = ">" if device.get("key") == selected_key else " "
        compact_rows.append(f"{marker}[{color}]{status:<9}[/] {_name(device, 27):<27} {_rssi(device):>8}")
    compact_rows.extend(
        (
            "",
            r"\[S] Scan  \[P] Pair  \[C] Connect  \[D] Disconnect",
            r"\[T] Trust  \[R] Refresh  \[X] Remove  \[G] Priority  \[M] Settings",
        )
    )
    return BluetoothConsoleView(
        header=header,
        topology=_topology(adapters, devices),
        legend="[bold cyan]LEGEND:[/]  [cyan]----[/] Strong (> -70 dBm)    [yellow]----[/] Weak (-70 to -85 dBm)    [red]----[/] Disconnected (< -85 dBm)",
        adapter_a=_adapter_table("ADAPTER A DEVICES (AUDIO)", adapter_a, devices, "cyan", selected_key),
        adapter_b=_adapter_table("ADAPTER B DEVICES (IO & CONTROLLERS)", adapter_b, devices, "green", selected_key),
        available=_available(devices, adapter_a, adapter_b, selected_key),
        actions=actions,
        adapter_status=_adapter_status(adapters, devices),
        diagnostics=_diagnostics(state, facts),
        recent_events=_events(state),
        help=help_text,
        footer=footer,
        compact="\n".join(compact_rows),
    )
