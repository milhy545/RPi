"""Pure rendering model for the Bluetooth terminal control center."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from rich.markup import escape


Device = dict[str, Any]
Adapter = dict[str, Any]

BT_TEXT = {
    "en": {
        "absent": "Absent",
        "adapter": "Adapter",
        "adapter_address": "Adapter Address",
        "adapter_a_title": "ADAPTER A DEVICES (AUDIO)",
        "adapter_b_title": "ADAPTER B DEVICES (IO & CONTROLLERS)",
        "adapter_priority": "Adapter Priority",
        "adapter_status": "ADAPTER STATUS",
        "adapters": "Adapters",
        "audio_input": "AUDIO INPUT DEVICES",
        "audio_output": "AUDIO OUTPUT DEVICES",
        "auto_connect": "Auto Connect",
        "available": "Available",
        "available_devices": "AVAILABLE DEVICES",
        "bluetooth_service": "Bluetooth Service",
        "connected": "Connected",
        "connect": "Connect",
        "connections": "Connections",
        "controllers": "CONTROLLERS & IO DEVICES",
        "degraded": "Degraded",
        "device": "Device",
        "device_name": "Device Name",
        "diagnostics": "DIAGNOSTICS",
        "disconnect": "Disconnect Device",
        "disconnect_short": "Disconnect",
        "disconnected": "Disconnected",
        "discoverable": "Discoverable",
        "dual_management": "Dual Adapter Management",
        "help": "HELP",
        "host_controller": "Host Controller",
        "io_devices": "IO DEVICES",
        "legend": "LEGEND",
        "more_settings": "More Settings",
        "navigate": "Navigate",
        "no_audio_inputs": "No audio inputs",
        "no_audio_outputs": "No audio outputs",
        "no_controllers": "No controllers",
        "no_event": "No event",
        "no_io_devices": "No IO devices",
        "none": "None",
        "not_present": "Not Present",
        "pair_new": "Pair New Device",
        "pair": "Pair",
        "paired": "Paired",
        "pairable": "Pairable",
        "powered_off": "Powered Off",
        "powered_on": "Powered On",
        "press_pair": "Press [yellow]\\[P][/] to pair selected device",
        "quick_actions": "QUICK ACTIONS",
        "quit": "Quit",
        "recent_events": "RECENT EVENTS",
        "refresh": "Refresh",
        "refresh_topology": "Refresh Topology",
        "remove": "Remove Paired Device",
        "remove_short": "Remove",
        "running": "Running",
        "scan": "Scan",
        "scan_all": "Scan All",
        "scan_all_adapters": "Scan All Adapters",
        "select_action": "Select Action",
        "service": "Service",
        "settings": "Settings",
        "strong": "Strong",
        "switch_panel": "Switch Panel",
        "priority": "Priority",
        "target": "Target",
        "topology": "TOPOLOGY",
        "total_connected": "Total Connected",
        "total_paired": "Total Paired",
        "trust": "Trust",
        "trust_device": "Trust Device",
        "uptime": "Uptime",
        "weak": "Weak",
    },
    "cz": {
        "absent": "Nepritomne",
        "adapter": "Adapter",
        "adapter_address": "Adresa Adapteru",
        "adapter_a_title": "ADAPTER A ZARIZENI (AUDIO)",
        "adapter_b_title": "ADAPTER B ZARIZENI (IO A OVLADACE)",
        "adapter_priority": "Priorita Adapteru",
        "adapter_status": "STAV ADAPTERU",
        "adapters": "Adaptery",
        "audio_input": "AUDIO VSTUPNI ZARIZENI",
        "audio_output": "AUDIO VYSTUPNI ZARIZENI",
        "auto_connect": "Auto Pripojeni",
        "available": "Dostupne",
        "available_devices": "DOSTUPNA ZARIZENI",
        "bluetooth_service": "Bluetooth Sluzba",
        "connected": "Pripojeno",
        "connect": "Pripojit",
        "connections": "Pripojeni",
        "controllers": "OVLADACE A IO ZARIZENI",
        "degraded": "Omezeno",
        "device": "Zarizeni",
        "device_name": "Nazev Zarizeni",
        "diagnostics": "DIAGNOSTIKA",
        "disconnect": "Odpojit Zarizeni",
        "disconnect_short": "Odpojit",
        "disconnected": "Odpojeno",
        "discoverable": "Viditelne",
        "dual_management": "Sprava Dvou Adapteru",
        "help": "NAPOVEDA",
        "host_controller": "Radic Hostitele",
        "io_devices": "IO ZARIZENI",
        "legend": "LEGENDA",
        "more_settings": "Dalsi Nastaveni",
        "navigate": "Navigace",
        "no_audio_inputs": "Zadne audio vstupy",
        "no_audio_outputs": "Zadne audio vystupy",
        "no_controllers": "Zadne ovladace",
        "no_event": "Zadna udalost",
        "no_io_devices": "Zadna IO zarizeni",
        "none": "Zadny",
        "not_present": "Nepritomen",
        "pair_new": "Parovat Nove Zarizeni",
        "pair": "Parovat",
        "paired": "Sparovano",
        "pairable": "Parovatelne",
        "powered_off": "Vypnuty",
        "powered_on": "Zapnuty",
        "press_pair": "Stiskni [yellow]\\[P][/] pro parovani vybraneho zarizeni",
        "quick_actions": "RYCHLE AKCE",
        "quit": "Konec",
        "recent_events": "POSLEDNI UDALOSTI",
        "refresh": "Obnovit",
        "refresh_topology": "Obnovit Topologii",
        "remove": "Odebrat Sparovane",
        "remove_short": "Odebrat",
        "running": "Bezi",
        "scan": "Sken",
        "scan_all": "Sken Vsech",
        "scan_all_adapters": "Sken Vsech Adapteru",
        "select_action": "Vybrat Akci",
        "service": "Sluzba",
        "settings": "Nastaveni",
        "strong": "Silny",
        "switch_panel": "Zmenit Panel",
        "priority": "Priorita",
        "target": "Cil",
        "topology": "TOPOLOGIE",
        "total_connected": "Celkem Pripojeno",
        "total_paired": "Celkem Sparovano",
        "trust": "Duverovat",
        "trust_device": "Duverovat Zarizeni",
        "uptime": "Doba Behu",
        "weak": "Slaby",
    },
}


def _text(language: str, key: str) -> str:
    return BT_TEXT.get(language, BT_TEXT["en"]).get(key, BT_TEXT["en"][key])


def _ascii(value: Any, width: int | None = None) -> str:
    rendered = str(value).encode("ascii", errors="replace").decode("ascii")
    return rendered[:width] if width is not None else rendered


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


def normalize_device_keys(devices: list[Device]) -> list[Device]:
    """Copy device records and provide a stable selection key for legacy data."""
    normalized = []
    for index, device in enumerate(devices):
        item = dict(device)
        item["key"] = (
            item.get("key")
            or item.get("device_key")
            or item.get("address")
            or item.get("mac")
            or f"legacy-device-{index}"
        )
        normalized.append(item)
    return normalized


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
    return _ascii(value, width)


def _rssi_value(device: Device) -> int | None:
    value = device.get("rssi")
    return int(value) if isinstance(value, int | float) else None


def _rssi(device: Device) -> str:
    value = _rssi_value(device)
    return f"{value} dBm" if value is not None else "-- dBm"


def _avg_rssi(devices: list[Device]) -> str:
    values = [value for device in devices if (value := _rssi_value(device)) is not None]
    return str(round(sum(values) / len(values))) if values else "--"


def _status(device: Device, language: str = "en") -> tuple[str, str]:
    if device.get("connected"):
        return _text(language, "connected"), "green"
    if device.get("paired"):
        return _text(language, "paired"), "cyan"
    if device.get("present") is False:
        return _text(language, "absent"), "red"
    return _text(language, "available"), "yellow"


def _power(adapter: Adapter, language: str = "en") -> tuple[str, str]:
    if not adapter:
        return _text(language, "not_present"), "red"
    if adapter.get("powered"):
        return _text(language, "powered_on"), "green"
    return _text(language, "powered_off"), "red"


def _adapter_devices(adapter: Adapter, devices: list[Device]) -> list[Device]:
    """Return devices assigned to a real adapter slot, never an empty placeholder."""
    adapter_id = adapter.get("id") if adapter else None
    if not adapter_id:
        return []
    return [device for device in devices if device.get("adapter_id") == adapter_id]


def _device_category_rows(devices: list[Device], category: str, language: str = "en") -> list[str]:
    matching = [device for device in devices if classify_device(device) == category]
    rows = []
    for device in matching[:4]:
        rows.append(f"|-- {_name(device, 13):<13} {_rssi(device):>7}")
    placeholder = {
        "audio_output": _text(language, "no_audio_outputs"),
        "audio_input": _text(language, "no_audio_inputs"),
        "io": _text(language, "no_io_devices"),
        "controller": _text(language, "no_controllers"),
    }[category]
    if not rows:
        rows.append(f"|-- {placeholder}")
    while len(rows) < 4:
        rows.append("|-- --")
    return rows


def _topology_cell(value: str, color: str = "") -> str:
    cell = f"{value[:27]:<27}"
    return f"[{color}]{cell}[/]" if color else cell


def _topology(adapters: list[Adapter], devices: list[Device], language: str = "en") -> str:
    adapter_a, adapter_b = adapter_slots(adapters)
    devices_a = _adapter_devices(adapter_a, devices)
    devices_b = _adapter_devices(adapter_b, devices)
    categories = {
        name: _device_category_rows(devices, name, language)
        for name in ("audio_output", "audio_input", "io", "controller")
    }
    a_power, a_color = _power(adapter_a, language)
    b_power, b_color = _power(adapter_b, language)
    adapter_a_rows = [f"{a_power} RSSI {_avg_rssi(devices_a)}", "       /\\", "    --< BT >--", r"       \/"]
    adapter_b_rows = [f"{b_power} RSSI {_avg_rssi(devices_b)}", "       /\\", "    --< BT >--", r"       \/"]
    lines = [
        f"[bold cyan]{_text(language, 'topology')}[/]",
        "".join(
            _topology_cell(title, color)
            for title, color in (
                (_text(language, "audio_output"), "bold cyan"),
                ("ADAPTER A / AUDIO", "bold cyan"),
                (_text(language, "audio_input"), "bold cyan"),
                (_text(language, "io_devices"), "bold green"),
                ("ADAPTER B / IO", "bold green"),
                (_text(language, "controllers"), "bold green"),
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
                    f"{len([d for d in devices_a if d.get('connected')])} {_text(language, 'connected')} / "
                    f"{len([d for d in devices_a if not d.get('connected')])} {_text(language, 'available')}",
                    "cyan",
                ),
                _topology_cell(""),
                _topology_cell(""),
                _topology_cell(
                    f"{len([d for d in devices_b if d.get('connected')])} {_text(language, 'connected')} / "
                    f"{len([d for d in devices_b if not d.get('connected')])} {_text(language, 'available')}",
                    "green",
                ),
                _topology_cell(""),
            )
        )
    )
    return "\n".join(lines)


def _adapter_table(
    title: str, adapter: Adapter, devices: list[Device], color: str, selected_key: str, language: str = "en"
) -> str:
    rows = [
        f"[bold {color}]{title}[/]",
        f" # {_text(language, 'device'):<14} RSSI    Status",
        "--------------------------------------",
    ]
    adapter_devices = _adapter_devices(adapter, devices)
    for index, device in enumerate(adapter_devices[:4], start=1):
        status, status_color = _status(device, language)
        marker = ">" if device.get("key") == selected_key else " "
        rows.append(f"{marker}{index} {_name(device, 12):<12} {_rssi(device):>7} [{status_color}]{status}[/]")
    while len(rows) < 7:
        rows.append("[dim]- --                   --      --[/]")
    rows.append(f"[{color}]{_text(language, 'adapter_address')}:[/] {adapter.get('address', '--')}")
    return "\n".join(rows)


def _available(
    devices: list[Device], adapter_a: Adapter, adapter_b: Adapter, selected_key: str, language: str = "en"
) -> str:
    labels = {
        adapter.get("id"): label
        for adapter, label in ((adapter_a, "A"), (adapter_b, "B"))
        if adapter.get("id")
    }
    rows = [
        f"[bold yellow]{_text(language, 'available_devices')}[/]",
        f"{_text(language, 'device_name'):<17} RSSI    {_text(language, 'adapter')}",
        "--------------------------------------",
    ]
    available = [device for device in devices if not device.get("connected")]
    for device in available[:4]:
        marker = ">" if device.get("key") == selected_key else " "
        rows.append(f"{marker}{_name(device, 14):<14} {_rssi(device):>7} {labels.get(device.get('adapter_id'), '-')}")
    while len(rows) < 7:
        rows.append("[dim]--                   --      -[/]")
    rows.append(_text(language, "press_pair"))
    return "\n".join(rows)


def _adapter_status(adapters: list[Adapter], devices: list[Device], language: str = "en") -> str:
    rows = [f"[bold cyan]{_text(language, 'adapter_status')}[/]"]
    for label, adapter in zip(("A", "B"), adapter_slots(adapters), strict=True):
        adapter_devices = _adapter_devices(adapter, devices)
        power, color = _power(adapter, language)
        rows.extend(
            [
                f"Adapter {label}: [{color}]{power}[/]",
                f"  {_text(language, 'connections')}: {len([d for d in adapter_devices if d.get('connected')])}  "
                f"{_text(language, 'available')}: {len([d for d in adapter_devices if not d.get('connected')])}",
                f"  RSSI (Avg): {_avg_rssi(adapter_devices)} dBm  TX Power: {adapter.get('tx_power', '--')} dBm",
            ]
        )
    return "\n".join(rows)


def _diagnostics(state: dict[str, Any], facts: dict[str, str], language: str = "en") -> str:
    adapters = state.get("adapters") or []
    backend = state.get("backend") or {}
    running = backend.get("available", True) and not backend.get("degraded")
    controllers = ", ".join(f"hci{adapter.get('index', '?')}" for adapter in adapters) or "none"
    return "\n".join(
        [
            f"[bold cyan]{_text(language, 'diagnostics')}[/]",
            f"{_text(language, 'bluetooth_service')}: "
            f"[{'green' if running else 'red'}]{_text(language, 'running' if running else 'degraded')}[/]",
            f"{_text(language, 'host_controller')}: [green]{controllers}[/]",
            f"{_text(language, 'discoverable')}: {'ON' if any(a.get('discoverable') for a in adapters) else 'OFF'}",
            f"{_text(language, 'pairable')}: {'ON' if any(a.get('pairable') for a in adapters) else 'OFF'}",
            f"{_text(language, 'uptime')}: {facts.get('uptime', '--')}",
            f"Kernel: {facts.get('kernel', '--')}",
            f"BlueZ: {facts.get('bluez', backend.get('name', '--'))}",
        ]
    )


def _events(state: dict[str, Any], language: str = "en") -> str:
    rows = [f"[bold cyan]{_text(language, 'recent_events')}[/]"]
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
        rows.append(f"[dim]--:--:-- {_text(language, 'no_event')}[/]")
    return "\n".join(rows)


def build_bluetooth_console(
    state: dict[str, Any] | None,
    *,
    facts: dict[str, str] | None = None,
    cpu_percent: float | None = None,
    memory_percent: float | None = None,
    language: str = "en",
) -> BluetoothConsoleView:
    """Build every visible Bluetooth TUI panel from one backend state snapshot."""
    state = state or {}
    facts = facts or {}
    adapters = list(state.get("adapters") or [])
    devices = normalize_device_keys(list(state.get("devices") or []))
    adapter_a, adapter_b = adapter_slots(adapters)
    backend = state.get("backend") or {}
    connected = len([device for device in devices if device.get("connected")])
    paired = len([device for device in devices if device.get("paired")])
    auto_connect = (state.get("settings") or {}).get("auto_connect", True)
    selected_key = str(state.get("selected_device_key") or "")
    selected_device = next((device for device in devices if device.get("key") == selected_key), None)
    selected_name = _name(selected_device, 18) if selected_device else _text(language, "none")
    degraded = bool(backend.get("degraded") or backend.get("available") is False)
    service = _text(language, "degraded" if degraded else "running")
    service_color = "red" if degraded else "green"
    cpu = "--" if cpu_percent is None else f"{cpu_percent:.0f}%"
    memory = "--" if memory_percent is None else f"{memory_percent:.0f}%"
    header = (
        "[bold cyan](BT)[/] [bold]RPi Bluetooth Control Center (TUI)[/]  "
        f"[cyan]{_text(language, 'dual_management')}[/]                         "
        f"{_text(language, 'auto_connect')}: "
        f"[{'green' if auto_connect else 'red'}]{'ON' if auto_connect else 'OFF'}[/] | "
        f"\\[S] {_text(language, 'scan_all')}  \\[P] {_text(language, 'pair_new')}  "
        f"\\[T] {_text(language, 'trust')}  \\[R] {_text(language, 'refresh')}  "
        f"\\[Q] {_text(language, 'quit')}"
    )
    actions = "\n".join(
        [
            f"[bold magenta]{_text(language, 'quick_actions')}[/]",
            f"\\[S] {_text(language, 'scan_all_adapters')}",
            f"\\[P] {_text(language, 'pair_new')}",
            f"\\[C] {_text(language, 'connect')}",
            f"\\[D] {_text(language, 'disconnect')}",
            f"\\[R] {_text(language, 'refresh_topology')}",
            f"\\[X] {_text(language, 'remove')}",
            f"\\[G] {_text(language, 'adapter_priority')}",
            f"\\[M] {_text(language, 'more_settings')}",
        ]
    )
    help_text = "\n".join(
        [
            f"[bold cyan]{_text(language, 'help')}[/]",
            f"Up/Down  {_text(language, 'navigate')}",
            f"Enter    {_text(language, 'select_action')}",
            f"Tab      {_text(language, 'switch_panel')}",
            f"T        {_text(language, 'trust_device')}",
            f"R        {_text(language, 'refresh')}",
            f"Q        {_text(language, 'quit')}",
        ]
    )
    footer = (
        f"{_text(language, 'bluetooth_service')}: [{service_color}]{service}[/]     "
        f"{_text(language, 'total_connected')}: [green]{connected}[/] | "
        f"{_text(language, 'total_paired')}: [cyan]{paired}[/]     "
        f"{_text(language, 'target')}: [yellow]{selected_name}[/]     "
        f"RPI OS: {facts.get('os', '--')} | CPU: {cpu} | Mem: {memory}"
    )
    compact_rows = [
        f"[bold cyan](BT)[/] [bold]RPi Bluetooth Control Center[/] | Auto: {'ON' if auto_connect else 'OFF'}",
        f"{_text(language, 'service')} [{service_color}]{service}[/] | "
        f"{_text(language, 'adapters')} {len(adapters)} | {_text(language, 'connected')} {connected} | "
        f"{_text(language, 'paired')} {paired}",
        "[cyan]A / AUDIO[/] "
        + (
            f"{escape(_ascii(adapter_a.get('alias') or adapter_a.get('id'), 27))} {_power(adapter_a, language)[0]}"
            if adapter_a
            else _text(language, "not_present")
        ),
        "[green]B / IO[/]    "
        + (
            f"{escape(_ascii(adapter_b.get('alias') or adapter_b.get('id'), 27))} {_power(adapter_b, language)[0]}"
            if adapter_b
            else _text(language, "not_present")
        ),
    ]
    for device in devices[:2]:
        status, color = _status(device, language)
        marker = ">" if device.get("key") == selected_key else " "
        compact_rows.append(f"{marker}[{color}]{status:<9}[/] {_name(device, 27):<27} {_rssi(device):>8}")
    compact_rows.extend(
        (
            "",
            f"\\[S] {_text(language, 'scan')}  \\[P] {_text(language, 'pair')}  "
            f"\\[C] {_text(language, 'connect')}  \\[D] {_text(language, 'disconnect_short')}",
            f"\\[T] {_text(language, 'trust')}  \\[R] {_text(language, 'refresh')}  "
            f"\\[X] {_text(language, 'remove_short')}  \\[G] {_text(language, 'priority')}  "
            f"\\[M] {_text(language, 'settings')}",
        )
    )
    return BluetoothConsoleView(
        header=header,
        topology=_topology(adapters, devices, language),
        legend=f"[bold cyan]{_text(language, 'legend')}:[/]  [cyan]----[/] {_text(language, 'strong')} (> -70 dBm)    "
        f"[yellow]----[/] {_text(language, 'weak')} (-70 to -85 dBm)    "
        f"[red]----[/] {_text(language, 'disconnected')} (< -85 dBm)",
        adapter_a=_adapter_table(
            _text(language, "adapter_a_title"), adapter_a, devices, "cyan", selected_key, language
        ),
        adapter_b=_adapter_table(
            _text(language, "adapter_b_title"), adapter_b, devices, "green", selected_key, language
        ),
        available=_available(devices, adapter_a, adapter_b, selected_key, language),
        actions=actions,
        adapter_status=_adapter_status(adapters, devices, language),
        diagnostics=_diagnostics(state, facts, language),
        recent_events=_events(state, language),
        help=help_text,
        footer=footer,
        compact="\n".join(compact_rows),
    )
