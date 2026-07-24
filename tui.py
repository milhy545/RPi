from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Log, Button, TabbedContent, TabPane, OptionList, Switch, Label, Input
from textual.reactive import reactive
import time
import os
import sys
import socket
import asyncio
import shlex
import threading
import urllib.error
import urllib.request
from datetime import datetime
from http.server import ThreadingHTTPServer
from aiohttp import web
from mode_switcher import ModeSwitcher, ModeSwitcherState
from config import TUI_STATS_INTERVAL, TUI_SETTINGS_INTERVAL
from rpi_dashboard.services import devices as devices_service
from rpi_dashboard.tui.bluetooth_console import build_bluetooth_console, normalize_device_keys
from rpi_dashboard.tui.formatting import human_audio_sink
from rpi_dashboard.api.routes import get_route


API_PORT = int(os.getenv("RPIDASHBOARD_API_PORT", "8090"))

I18N = {
    "cz": {
        "language": "Jazyk",
        "player": "Prehravac",
        "apps": "Aplikace",
        "audio": "Audio",
        "bluetooth": "Bluetooth",
        "devices": "Zarizeni",
        "network": "Sit",
        "system": "System",
        "logs": "Logy",
        "input_url": "YouTube nebo prima URL...",
        "start_mpv": "Spustit MPV",
        "start_steam": "Spustit Steam Link",
        "stop_all": "Zastavit vse",
        "open_terminal": "Otevrit terminal",
        "player_return": "Navrat: ukonci prehravani nebo pouzij Zastavit vse z Aplikaci/WebUI.",
        "apps_return": "Terminal: Ctrl-b, potom d. Aplikace: ukonci aplikaci nebo Zastavit vse.",
        "mode_current": "Aktualni rezim",
        "audio_title": "Zvukovy vystup (DLNA/BT/HDMI)",
        "dlna_latency": "DLNA latence (ms):",
        "save_latency": "Ulozit latenci",
        "restart_padlna": "Restart pa-dlna",
        "bt_title": "Bluetooth zarizeni",
        "bt_controller_title": "Xbox / ovladace",
        "bt_controller_ready": "Pripraveno",
        "bt_controller_not_ready": "Neni pripraveno",
        "devices_title": "Zarizeni",
        "devices_info": "Wi-Fi, hotspot a stav hardwaru jsou v Sit/System. Bluetooth ma vlastni zalozku.",
        "scan": "Skenovat",
        "pair": "Parovat",
        "trust": "Duverovat",
        "connect": "Pripojit",
        "disconnect": "Odpojit",
        "remove": "Odebrat",
        "network_title": "Sit a Tailscale",
        "network_loading": "Nacitam sitove informace...",
        "wifi_title": "Wi-Fi a zachranny hotspot",
        "scan_wifi": "Skenovat Wi-Fi",
        "wifi_password": "Heslo (nepovinne pro otevrene site)",
        "connect_wifi": "Pripojit vybranou sit",
        "hotspot_hidden": "Hotspot SSID: RPi-service (skryta)",
        "hotspot_clients": "Pripojeni klienti: --",
        "rescue_hotspot": "Zachranny hotspot: ",
        "no_bt": "Zadna sparovana Bluetooth zarizeni. Pouzij Skenovat, potom Parovat.",
        "no_wifi": "Zadne Wi-Fi site nenalezeny. Spust sken znovu nebo zkontroluj adapter.",
        "tailscale_inactive": "Tailscale: neaktivni nebo nenainstalovano",
        "loaded": "[SYSTEM] J.A.R.V.I.S. Dumb TV Interface nacteno.",
        "listening": "[NETWORK] Nasloucham na portu {port}...",
        "waiting": "[DAEMON] Cekam na prikazy z lokalni site.",
        "terminal_help": "[HELP] Navrat do dashboardu z terminalu: stiskni Ctrl-b, potom d.",
        "app_help": "[HELP] Navrat do dashboardu: ukonci aplikaci, nebo pouzij Zastavit vse v TUI/WebUI.",
    },
    "en": {
        "language": "Language",
        "player": "Player",
        "apps": "Apps",
        "audio": "Audio",
        "bluetooth": "Bluetooth",
        "devices": "Devices",
        "network": "Network",
        "system": "System",
        "logs": "Logs",
        "input_url": "YouTube or direct URL...",
        "start_mpv": "Start MPV",
        "start_steam": "Start Steam Link",
        "stop_all": "Stop all",
        "open_terminal": "Open Terminal",
        "player_return": "Return: quit playback or use Stop all from Apps/WebUI.",
        "apps_return": "Terminal return: Ctrl-b, then d. Apps return: quit app or Stop all.",
        "mode_current": "Current mode",
        "audio_title": "Audio output (DLNA/BT/HDMI)",
        "dlna_latency": "DLNA latency (ms):",
        "save_latency": "Save latency",
        "restart_padlna": "Restart pa-dlna",
        "bt_title": "Bluetooth devices",
        "bt_controller_title": "Xbox / controllers",
        "bt_controller_ready": "Ready",
        "bt_controller_not_ready": "Not ready",
        "devices_title": "Devices",
        "devices_info": "Wi-Fi, hotspot, and hardware status live in Network/System. Bluetooth has its own tab.",
        "scan": "Scan",
        "pair": "Pair",
        "trust": "Trust",
        "connect": "Connect",
        "disconnect": "Disconnect",
        "remove": "Remove",
        "network_title": "Network and Tailscale",
        "network_loading": "Loading network information...",
        "wifi_title": "Wi-Fi and rescue hotspot",
        "scan_wifi": "Scan Wi-Fi",
        "wifi_password": "Password (optional for open networks)",
        "connect_wifi": "Connect selected network",
        "hotspot_hidden": "Hotspot SSID: RPi-service (hidden)",
        "hotspot_clients": "Connected clients: --",
        "rescue_hotspot": "Rescue hotspot: ",
        "no_bt": "No paired Bluetooth devices. Use Scan, then Pair.",
        "no_wifi": "No Wi-Fi networks found. Run scan again or check adapter.",
        "tailscale_inactive": "Tailscale: inactive or not installed",
        "loaded": "[SYSTEM] J.A.R.V.I.S. Dumb TV Interface loaded.",
        "listening": "[NETWORK] Listening on port {port}...",
        "waiting": "[DAEMON] Waiting for local network commands.",
        "terminal_help": "[HELP] Return to dashboard from terminal: press Ctrl-b, then d.",
        "app_help": "[HELP] Return to dashboard: quit the app, or use Stop all from the TUI/WebUI if it remains active.",
    },
}


def normalize_lang(lang: str | None) -> str:
    return "en" if (lang or "").lower() == "en" else "cz"


def t(lang: str, key: str) -> str:
    lang = normalize_lang(lang)
    return I18N[lang].get(key, I18N["cz"].get(key, key))

class SystemStats(Static):
    """Show live system load from /proc and /sys."""
    def on_mount(self) -> None:
        from rpi_dashboard.services.bluetooth import service as bluetooth_service

        bluetooth_service.start_startup_recovery()
        self._settings_cache = {
            "network": 0.0,
            "audio": 0.0,
            "bluetooth": 0.0,
            "wifi": 0.0
        }
        self._settings_cache_ttl = 10.0

        # State used to compute CPU deltas.
        self._prev_cpu_idle = 0
        self._prev_cpu_total = 0
        self.update_stats()
        self.set_interval(TUI_STATS_INTERVAL, self.update_stats)
        
    def get_cpu_usage(self) -> float:
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
            if line.startswith("cpu "):
                parts = list(map(int, line.split()[1:8]))
                idle = parts[3] + parts[4]
                total = sum(parts)
                
                if self._prev_cpu_total > 0:
                    diff_idle = idle - self._prev_cpu_idle
                    diff_total = total - self._prev_cpu_total
                    if diff_total > 0:
                        cpu_pct = 100.0 * (1.0 - diff_idle / diff_total)
                    else:
                        cpu_pct = 0.0
                else:
                    # First measurement.
                    cpu_pct = 0.0
                self._prev_cpu_idle = idle
                self._prev_cpu_total = total
                return cpu_pct
        except Exception as e:
            return 0.0
        return 0.0

    def get_ram_usage(self) -> tuple[float, float]:
        try:
            mem_total = 0
            mem_available = 0
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        mem_total = int(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        mem_available = int(line.split()[1])
            if mem_total > 0:
                used = mem_total - mem_available
                return used / 1024 / 1024, mem_total / 1024 / 1024
        except Exception:
            pass
        return 0.45, 1.0

    def get_cpu_temp(self) -> float:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return int(f.read().strip()) / 1000.0
        except Exception as e:
            try:
                with open("/sys/class/thermal/thermal_zone1/temp", "r") as f:
                    return int(f.read().strip()) / 1000.0
            except Exception as e:
                return 45.0

    def get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.254.254.254', 1))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            ip = '127.0.0.1'
        return ip

    def update_stats(self) -> None:
        cpu = self.get_cpu_usage()
        ram_used, ram_total = self.get_ram_usage()
        temp = self.get_cpu_temp()
        ip = self.get_local_ip()
        
        if ram_total <= 1.5:
            ram_str = f"{int(ram_used * 1024)}MB/{int(ram_total * 1024)}MB"
        else:
            ram_str = f"{ram_used:.1f}GB/{ram_total:.1f}GB"
            
        self.update(
            f"CPU: {cpu:.1f}% | "
            f"RAM: {ram_str} | "
            f"TEMP: {temp:.1f}C | "
            f"IP: {ip}"
        )


class TopStatus(Static):
    """Compact ASCII-safe status line for the physical TV console."""

    def on_mount(self) -> None:
        self._prev_cpu_idle = 0
        self._prev_cpu_total = 0
        self.update_status()
        self.set_interval(TUI_STATS_INTERVAL, self.update_status)

    def get_cpu_usage(self) -> float:
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
            if line.startswith("cpu "):
                parts = list(map(int, line.split()[1:8]))
                idle = parts[3] + parts[4]
                total = sum(parts)
                if self._prev_cpu_total > 0:
                    diff_idle = idle - self._prev_cpu_idle
                    diff_total = total - self._prev_cpu_total
                    cpu_pct = 100.0 * (1.0 - diff_idle / diff_total) if diff_total > 0 else 0.0
                else:
                    cpu_pct = 0.0
                self._prev_cpu_idle = idle
                self._prev_cpu_total = total
                return cpu_pct
        except Exception:
            return 0.0
        return 0.0

    def get_ram_usage(self) -> tuple[float, float]:
        try:
            mem_total = 0
            mem_available = 0
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        mem_total = int(line.split()[1])
                    elif line.startswith("MemAvailable:"):
                        mem_available = int(line.split()[1])
            if mem_total > 0:
                used = mem_total - mem_available
                return used / 1024 / 1024, mem_total / 1024 / 1024
        except Exception:
            pass
        return 0.45, 1.0

    def get_cpu_temp(self) -> float:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return int(f.read().strip()) / 1000.0
        except Exception:
            return 45.0

    def get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('10.254.254.254', 1))
            ip = s.getsockname()[0]
            s.close()
        except Exception:
            ip = '127.0.0.1'
        return ip

    def update_status(self) -> None:
        cpu = self.get_cpu_usage()
        ram_used, ram_total = self.get_ram_usage()
        temp = self.get_cpu_temp()
        ip = self.get_local_ip()
        mode = "IDLE"
        app = getattr(self, "app", None)
        if app is not None and hasattr(app, "mode_switcher"):
            try:
                mode = app.mode_switcher.state.name
            except Exception:
                mode = "IDLE"
        self.update(
            f"MODE: {mode} | CPU: {cpu:.1f}% | "
            f"RAM: {int(ram_used * 1024)}MB/{int(ram_total * 1024)}MB | "
            f"TEMP: {temp:.1f}C | IP: {ip} | API: {API_PORT}"
        )

class ModeStatus(Static):
    """Show the current RPi mode."""
    current_mode = reactive("IDLE (Dashboard)")

    def render(self) -> str:
        app = getattr(self, "app", None)
        lang = getattr(app, "language", "cz")
        return f"{t(lang, 'mode_current')}: [bold green]{self.current_mode}[/]"



class RPiDashboard(App):
    """Hacker-style TUI Dashboard pro RPi."""
    language = reactive(normalize_lang(os.getenv("RPIDASHBOARD_LANG", "cz")))

    CSS = """
    Screen {
        background: $surface-darken-1;
    }
    #top_status {
        height: 1;
        padding: 0 1;
        background: $panel;
        color: $text;
    }
    #language_switch {
        height: 3;
        padding: 0 1;
        background: $panel;
        content-align: center middle;
    }
    #language_label {
        width: 1fr;
        content-align: left middle;
    }
    .lang-button {
        width: 8;
        margin: 0 1 0 0;
    }
    TabbedContent {
        height: 1fr;
    }
    TabPane {
        height: 1fr;
    }
    #sidebar {
        width: 30;
        dock: left;
        padding: 1;
        background: $panel;
        height: 100%;
    }
    #main-content {
        padding: 1;
        height: 100%;
    }
    SystemStats {
        padding: 1;
        background: $surface;
        border: solid $accent;
        content-align: center middle;
    }
    ModeStatus {
        padding: 1;
        background: $surface;
        border: solid green;
        margin-top: 1;
        content-align: center middle;
    }
    Log {
        margin-top: 1;
        border: solid $secondary;
        height: 1fr;
    }
    Button {
        width: 100%;
        margin-bottom: 1;
    }
    .mpv-url-input {
        width: 100%;
        margin-bottom: 1;
        background: $surface;
        border: solid $accent;
    }
    #settings-container {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
        padding: 1;
        height: 1fr;
    }
    .settings-panel {
        background: $surface;
        border: solid $secondary;
        padding: 1;
        height: 100%;
    }
    .settings-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    #panel_bluetooth { padding: 0; border: none; }
    #title_bluetooth { display: none; }
    #bt_full { height: auto; }
    #txt_bt_header {
        height: 2;
        padding: 0 1;
        content-align: left middle;
        background: $surface-darken-1;
    }
    #txt_bluetooth_topology { height: 11; border: solid cyan; }
    #txt_bt_legend {
        height: 3;
        border: solid $secondary;
        padding: 0 1;
        content-align: center middle;
    }
    #bt_terminal_middle { height: 11; }
    #bt_terminal_bottom { height: 11; }
    .bt-terminal-panel {
        border: solid $accent;
        padding: 0 1;
        background: $surface;
        color: $text;
    }
    #bt_terminal_middle .bt-terminal-panel,
    #bt_terminal_bottom .bt-terminal-panel {
        width: 1fr;
        height: 100%;
    }
    #txt_bluetooth_adapter_a,
    #txt_bt_adapter_status { border: solid cyan; }
    #txt_bluetooth_adapter_b { border: solid green; }
    #txt_bluetooth_available { border: solid yellow; }
    #txt_bluetooth_actions { border: solid magenta; }
    #txt_bt_diagnostics,
    #txt_bt_events,
    #txt_bt_help { border: solid $secondary; }
    #txt_bt_footer {
        height: 1;
        padding: 0 1;
        background: $surface-darken-1;
    }
    #bt_legacy_controls {
        display: none;
        height: 5;
        border: solid $secondary;
        margin-top: 1;
        padding: 0 1;
    }
    #list_bluetooth_devices { height: 5; }
    #bt_legacy_buttons { height: 3; }
    #bt_legacy_buttons Button { margin: 0 1 0 0; min-width: 11; }
    #txt_bt_compact { display: none; height: 1fr; border: solid cyan; padding: 0 1; }
    #panel_bluetooth.bt-compact #bt_full { display: none; }
    #panel_bluetooth.bt-compact #txt_bt_compact { display: block; }
    #panel_bluetooth.bt-compact #bt_legacy_controls { display: block; margin-top: 0; }
    #panel_bluetooth.bt-compact #list_bluetooth_devices { height: 4; }
    #panel_bluetooth.bt-compact #bt_legacy_buttons { display: none; }
    #panel_bluetooth.bt-compact { padding: 0; }
    #panel_bluetooth.bt-compact #bt_legacy_controls { height: 5; }
    #panel_bluetooth.bt-compact #txt_bt_compact { height: 1fr; }
    """

    def tr(self, key: str) -> str:
        return t(self.language, key)

    def compose(self) -> ComposeResult:
        initial_tab = os.getenv("RPIDASHBOARD_INITIAL_TAB", "tab_player")
        if initial_tab not in {
            "tab_player",
            "tab_apps",
            "tab_audio",
            "tab_bluetooth",
            "tab_devices",
            "tab_network",
            "tab_system",
            "tab_logs",
        }:
            initial_tab = "tab_player"
        yield Header(show_clock=True)
        yield TopStatus(id="top_status")
        with Horizontal(id="language_switch"):
            yield Static("", id="language_label")
            yield Button("CZ", id="btn_lang_cz", classes="lang-button")
            yield Button("EN", id="btn_lang_en", classes="lang-button")
        
        with TabbedContent(initial=initial_tab):
            with TabPane(self.tr("player"), id="tab_player"):
                with Vertical(id="main-content"):
                    yield Static("", id="title_player", classes="settings-title")
                    yield Input(placeholder=self.tr("input_url"), id="input_mpv_url", classes="mpv-url-input")
                    yield Button(self.tr("start_mpv"), id="btn_mpv", variant="success")
                    yield Static("", id="hint_player_return")
                    yield ModeStatus(id="mode_status")

            with TabPane(self.tr("apps"), id="tab_apps"):
                with Vertical(id="sidebar"):
                    yield Static("", id="title_apps", classes="title")
                    yield Button(self.tr("start_steam"), id="btn_steamlink", variant="primary")
                    yield Button("GeForce Now", id="btn_gfn", variant="default")
                    yield Button("Spotify WebOS", id="btn_spotify", variant="warning")
                    yield Button("Amazon Music", id="btn_amazon", variant="default")
                    yield Button(self.tr("stop_all"), id="btn_stop", variant="error")
                    yield Button(self.tr("open_terminal"), id="btn_terminal", variant="default")
                    yield Static("", id="hint_apps_return")

            with TabPane(self.tr("audio"), id="tab_audio"):
                with Vertical(classes="settings-panel", id="panel_audio"):
                    yield Static("", id="title_audio", classes="settings-title")
                    yield OptionList(id="list_audio_sinks")
                    with Horizontal():
                        yield Button("Vol -10%", id="btn_vol_down")
                        yield Button("Vol +10%", id="btn_vol_up")
                    yield Label("", id="label_dlna_latency")
                    yield Input(placeholder="0", id="input_dlna_latency")
                    yield Button(self.tr("save_latency"), id="btn_save_latency")
                    with Horizontal():
                        yield Label("Alexa AUX -> BT:")
                        yield Switch(id="switch_alexa_bt", value=False)
                    yield Button(self.tr("restart_padlna"), id="btn_restart_padlna", variant="default")

            with TabPane(self.tr("bluetooth"), id="tab_bluetooth"):
                with VerticalScroll(classes="settings-panel", id="panel_bluetooth"):
                    yield Static("", id="title_bluetooth", classes="settings-title")
                    with Vertical(id="bt_full"):
                        yield Static("", id="txt_bt_header")
                        yield Static("", id="txt_bluetooth_topology", classes="bt-terminal-panel")
                        yield Static("", id="txt_bt_legend")
                        with Horizontal(id="bt_terminal_middle"):
                            yield Static("", id="txt_bluetooth_adapter_a", classes="bt-terminal-panel")
                            yield Static("", id="txt_bluetooth_adapter_b", classes="bt-terminal-panel")
                            yield Static("", id="txt_bluetooth_available", classes="bt-terminal-panel")
                            yield Static("", id="txt_bluetooth_actions", classes="bt-terminal-panel")
                        with Horizontal(id="bt_terminal_bottom"):
                            yield Static("", id="txt_bt_adapter_status", classes="bt-terminal-panel")
                            yield Static("", id="txt_bt_diagnostics", classes="bt-terminal-panel")
                            yield Static("", id="txt_bt_events", classes="bt-terminal-panel")
                            yield Static("", id="txt_bt_help", classes="bt-terminal-panel")
                        yield Static("", id="txt_bt_footer")
                    yield Static("", id="txt_bt_compact")
                    with Vertical(id="bt_legacy_controls"):
                        yield OptionList(id="list_bluetooth_devices")
                        with Horizontal(id="bt_legacy_buttons"):
                            yield Button(self.tr("scan"), id="btn_scan_bluetooth", variant="primary")
                            yield Button(self.tr("pair"), id="btn_pair_bluetooth", variant="success")
                            yield Button(self.tr("trust"), id="btn_trust_bluetooth", variant="warning")
                            yield Button(self.tr("connect"), id="btn_connect_bluetooth", variant="success")
                            yield Button(self.tr("disconnect"), id="btn_disconnect_bluetooth", variant="error")
                            yield Button(self.tr("remove"), id="btn_remove_bluetooth", variant="error")

            with TabPane(self.tr("devices"), id="tab_devices"):
                with Vertical(classes="settings-panel", id="panel_devices"):
                    yield Static("", id="title_devices", classes="settings-title")
                    yield Static("Wi-Fi, hotspot, and hardware status live in Network/System. Bluetooth has its own tab.", id="txt_devices_info")

            with TabPane(self.tr("network"), id="tab_network"):
                with Horizontal():
                    with Vertical(classes="settings-panel", id="panel_network"):
                        yield Static("", id="title_network", classes="settings-title")
                        yield Static("", id="txt_network_info")
                        yield Static("Tailscale Status: --", id="txt_tailscale_info")
                    with Vertical(classes="settings-panel", id="panel_wifi"):
                        yield Static("", id="title_wifi", classes="settings-title")
                        yield OptionList(id="list_wifi_networks")
                        with Horizontal():
                            yield Button(self.tr("scan_wifi"), id="btn_scan_wifi", variant="primary")
                        yield Input(placeholder=self.tr("wifi_password"), id="input_wifi_password", password=True)
                        yield Button(self.tr("connect_wifi"), id="btn_connect_wifi", variant="success")
                        yield Static("", id="txt_hotspot_ssid")
                        yield Static("", id="txt_hotspot_clients")
                        with Horizontal():
                            yield Label("", id="label_rescue_hotspot")
                            yield Switch(id="switch_hotspot", value=True)
                        yield Static("Spotify Connect (Raspotify):")
                        with Horizontal():
                            yield Switch(id="switch_raspotify", value=True)

            with TabPane(self.tr("system"), id="tab_system"):
                with Vertical(id="main-content"):
                    yield Static("", id="title_system", classes="settings-title")
                    yield SystemStats()

            with TabPane(self.tr("logs"), id="tab_logs"):
                yield Log(id="syslog")
                            
        yield Footer()

    def write_log(self, message: str) -> None:
        """Write a message to the UI log and a file."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        try:
            os.makedirs("/home/milhy777", exist_ok=True)
            with open("/home/milhy777/dashboard.log", "a") as f:
                f.write(full_message + "\n")
        except Exception as e:
            print(f"[WARN] Failed to write dashboard log: {e}", file=sys.stderr)
        if hasattr(self, "mode_switcher"):
            self.mode_switcher.log_buffer.write(full_message)
        try:
            log_widget = self.query_one("#syslog", Log)
            log_widget.write_line(full_message)
        except Exception as e:
            # Widget not ready yet
            pass

    def set_button_label(self, selector: str, label: str) -> None:
        self.query_one(selector, Button).label = label

    def set_static_text(self, selector: str, text: str) -> None:
        self.query_one(selector, Static).update(text)

    def set_label_text(self, selector: str, text: str) -> None:
        self.query_one(selector, Label).update(text)

    def set_input_placeholder(self, selector: str, text: str) -> None:
        self.query_one(selector, Input).placeholder = text

    def set_tab_label(self, tab_id: str, label: str) -> None:
        tab = self.query_one(TabbedContent).get_tab(tab_id)
        if tab is not None:
            tab.label = label

    def empty_bt_label(self) -> str:
        return self.tr("no_bt")

    def empty_wifi_label(self) -> str:
        return self.tr("no_wifi")

    def apply_language(self) -> None:
        """Refresh visible labels after the CZ/EN switch changes."""
        lang_name = "Cestina" if self.language == "cz" else "English"
        self.set_static_text("#language_label", f"{self.tr('language')}: [bold]{lang_name}[/]")

        self.set_button_label("#btn_lang_cz", "CZ ON" if self.language == "cz" else "CZ")
        self.set_button_label("#btn_lang_en", "EN ON" if self.language == "en" else "EN")

        for tab_id, key in (
            ("tab_player", "player"),
            ("tab_apps", "apps"),
            ("tab_audio", "audio"),
            ("tab_bluetooth", "bluetooth"),
            ("tab_devices", "devices"),
            ("tab_network", "network"),
            ("tab_system", "system"),
            ("tab_logs", "logs"),
        ):
            self.set_tab_label(tab_id, self.tr(key))

        self.set_static_text("#title_player", f"[bold]{self.tr('player')}[/bold]")
        self.set_static_text("#title_apps", f"[bold]{self.tr('apps')}[/bold]")
        self.set_static_text("#title_audio", f"[bold]{self.tr('audio_title')}[/bold]")
        self.set_static_text("#title_bluetooth", f"[bold]{self.tr('bt_title')}[/bold]")
        self.set_static_text("#title_devices", f"[bold]{self.tr('devices_title')}[/bold]")
        self.set_static_text("#txt_devices_info", self.tr("devices_info"))
        self.set_static_text("#title_network", f"[bold]{self.tr('network_title')}[/bold]")
        self.set_static_text("#title_wifi", f"[bold]{self.tr('wifi_title')}[/bold]")
        self.set_static_text("#title_system", f"[bold]{self.tr('system')}[/bold]")

        self.set_input_placeholder("#input_mpv_url", self.tr("input_url"))
        self.set_input_placeholder("#input_wifi_password", self.tr("wifi_password"))

        self.set_button_label("#btn_mpv", self.tr("start_mpv"))
        self.set_button_label("#btn_steamlink", self.tr("start_steam"))
        self.set_button_label("#btn_stop", self.tr("stop_all"))
        self.set_button_label("#btn_terminal", self.tr("open_terminal"))
        self.set_button_label("#btn_save_latency", self.tr("save_latency"))
        self.set_button_label("#btn_restart_padlna", self.tr("restart_padlna"))
        self.set_button_label("#btn_scan_bluetooth", self.tr("scan"))
        self.set_button_label("#btn_pair_bluetooth", self.tr("pair"))
        self.set_button_label("#btn_trust_bluetooth", self.tr("trust"))
        self.set_button_label("#btn_connect_bluetooth", self.tr("connect"))
        self.set_button_label("#btn_disconnect_bluetooth", self.tr("disconnect"))
        self.set_button_label("#btn_remove_bluetooth", self.tr("remove"))
        self.set_button_label("#btn_scan_wifi", self.tr("scan_wifi"))
        self.set_button_label("#btn_connect_wifi", self.tr("connect_wifi"))

        self.set_label_text("#label_dlna_latency", self.tr("dlna_latency"))
        self.set_label_text("#label_rescue_hotspot", self.tr("rescue_hotspot"))

        self.set_static_text("#hint_player_return", self.tr("player_return"))
        self.set_static_text("#hint_apps_return", self.tr("apps_return"))
        self.set_static_text("#txt_network_info", self.tr("network_loading"))
        self.set_static_text("#txt_hotspot_ssid", self.tr("hotspot_hidden"))
        self.set_static_text("#txt_hotspot_clients", self.tr("hotspot_clients"))

        self.query_one("#mode_status", ModeStatus).refresh()

        bt_list = self.query_one("#list_bluetooth_devices", OptionList)
        if bt_list.option_count == 1 and str(bt_list.get_option_at_index(0).prompt) in {
            t("cz", "no_bt"),
            t("en", "no_bt"),
        }:
            bt_list.clear_options()
            bt_list.add_option(self.empty_bt_label())

        wifi_list = self.query_one("#list_wifi_networks", OptionList)
        if wifi_list.option_count == 1 and str(wifi_list.get_option_at_index(0).prompt) in {
            t("cz", "no_wifi"),
            t("en", "no_wifi"),
        }:
            wifi_list.clear_options()
            wifi_list.add_option(self.empty_wifi_label())

        if hasattr(self, "_bluetooth_state_snapshot"):
            self.render_bluetooth_console(
                self._bluetooth_state_snapshot,
                self._bluetooth_devices_snapshot,
                self._bluetooth_adapters_snapshot,
            )

    def replay_log_buffer(self) -> None:
        """Replay LogBuffer history into the Log widget (e.g. after resume)."""
        try:
            log_widget = self.query_one("#syslog", Log)
            log_widget.clear()
            if hasattr(self, "mode_switcher"):
                for line in self.mode_switcher.log_buffer.get_lines():
                    log_widget.write_line(line)
        except Exception as e:
            self.write_log(f"[WARN] Exception: {e}")

    def pause_api_server(self) -> None:
        """Flag the API server to reject incoming requests during TUI suspension."""
        self.write_log("[SYSTEM] Pausing API server requests.")
        self.api_server_paused = True

    def resume_api_server(self) -> None:
        """Flag the API server to resume processing requests."""
        self.write_log("[SYSTEM] Resuming API server requests.")
        self.api_server_paused = False

    def on_mount(self) -> None:
        self._settings_cache = {
            "network": 0.0,
            "audio": 0.0,
            "bluetooth": 0.0,
            "wifi": 0.0
        }
        self._settings_cache_ttl = 10.0
        self.mode_switcher = ModeSwitcher(self)
        self.apply_language()
        
        self.write_log(self.tr("loaded"))
        self.write_log(self.tr("listening").format(port=API_PORT))
        self.write_log(self.tr("waiting"))
        
        self.api_task = None
        if API_PORT > 0:
            self.api_task = asyncio.create_task(self.start_api_server())
        
        # Periodic settings panel updates (every TUI_SETTINGS_INTERVAL seconds)
        self.set_interval(TUI_SETTINGS_INTERVAL, self.update_settings_data)
        # Run immediately on mount
        asyncio.create_task(self.update_settings_data())

    async def run_sys_cmd(self, cmd: str, timeout: float = 5.0) -> str:
        """Helper to run a shell command asynchronously and return its output."""
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                self.write_log(f"[TIMEOUT] cmd exceeded {timeout}s: {cmd[:80]}")
                return ""
            if proc.returncode == 0:
                return stdout.decode(errors="replace").strip()
        except Exception as e:
            self.write_log(f"[ERROR] run_sys_cmd failed: {e}")
        return ""

    async def update_settings_data(self) -> None:
        """Refresh all settings panel widgets with system configuration data (with TTL and tab check)."""
        try:
            active_tab = self.query_one(TabbedContent).active
            if active_tab not in {"tab_audio", "tab_bluetooth", "tab_devices", "tab_network", "tab_system"}:
                return
        except Exception as e:
            return

        current_time = time.time()
        self._updating_settings = True
        try:
            if current_time - self._settings_cache["network"] > self._settings_cache_ttl:
                await self.update_network_info()
                self._settings_cache["network"] = current_time

            if current_time - self._settings_cache["audio"] > self._settings_cache_ttl:
                await self.update_audio_sinks()
                self._settings_cache["audio"] = current_time

            if current_time - self._settings_cache["bluetooth"] > self._settings_cache_ttl:
                await self.update_bluetooth_devices()
                self._settings_cache["bluetooth"] = current_time

            if current_time - self._settings_cache["wifi"] > self._settings_cache_ttl:
                await self.update_wifi_hotspot_info()
                self._settings_cache["wifi"] = current_time
        finally:
            self._updating_settings = False

    async def update_network_info(self) -> None:
        """Fetch and display active network interface IPs and Tailscale status."""
        try:
            # 1. Local IP
            local_ip = self.get_local_ip() if hasattr(self, "get_local_ip") else "127.0.0.1"
            # Get other interfaces via ip -br addr
            ip_info = await self.run_sys_cmd("ip -br addr | grep -v 'lo' | awk '{print $1 \": \" $3}'")
            ip_str = ip_info.replace("\n", " | ") if ip_info else f"eth0/wlan0: {local_ip}"
            self.query_one("#txt_network_info", Static).update(f"IPs: {ip_str}")
            
            # 2. Tailscale Status
            ts_ip = await self.run_sys_cmd("tailscale ip -4")
            if ts_ip:
                self.query_one("#txt_tailscale_info", Static).update(f"Tailscale IP: [bold green]{ts_ip}[/]")
            else:
                self.query_one("#txt_tailscale_info", Static).update(self.tr("tailscale_inactive"))
        except Exception as e:
            self.write_log(f"[WARN] Exception: {e}")

    async def update_audio_sinks(self) -> None:
        """Fetch and list available PulseAudio/PipeWire sinks."""
        try:
            sinks_list = self.query_one("#list_audio_sinks", OptionList)
            sinks_list.clear_options()
            self._audio_sink_by_prompt = {}
            
            # Get default sink name
            default_sink = await self.run_sys_cmd("pactl get-default-sink")
            
            # Get list of sinks
            sinks_out = await self.run_sys_cmd("pactl list short sinks")
            if not sinks_out:
                sinks_list.add_option("[ERROR] No audio outputs reported by pactl")
                return
                
            for line in sinks_out.split("\n"):
                parts = line.split()
                if len(parts) >= 2:
                    sink_id = parts[1]
                    item = human_audio_sink(sink_id, default=sink_id == default_sink)
                    label = f"{item.status} {item.primary} - {item.detail}".strip()
                    sinks_list.add_option(label)
                    self._audio_sink_by_prompt[label] = sink_id
            # Load and populate DLNA latency and Alexa loopback switch
            import webserver
            try:
                latency_data = webserver._load_audio_latency()
                lat = latency_data.get("dlna_output_offset_ms", 0)
                self.query_one("#input_dlna_latency", Input).value = str(lat)
            except Exception as e:
                pass
            try:
                loopback_active = bool(webserver._loopback_module_id())
                self.query_one("#switch_alexa_bt", Switch).value = loopback_active
            except Exception as e:
                pass
        except Exception as e:
            self.write_log(f"[WARN] Exception: {e}")

    async def update_bluetooth_devices(self) -> None:
        """Fetch and list paired Bluetooth devices."""
        try:
            bt_list = self.query_one("#list_bluetooth_devices", OptionList)
            bt_list.clear_options()
            self._bt_mac_by_prompt = {}
            self._bt_target_by_prompt = {}
            state = await asyncio.to_thread(devices_service.devices_state)
            bluetooth = state.get("bluetooth", {})
            v2 = bluetooth.get("v2") or {}
            devices = normalize_device_keys(v2.get("devices") or bluetooth.get("devices") or bluetooth.get("paired") or [])
            adapters = v2.get("adapters") or []
            self._bluetooth_state_snapshot = v2
            self._bluetooth_devices_snapshot = devices
            self._bluetooth_adapters_snapshot = adapters

            if not devices:
                bt_list.add_option(self.empty_bt_label())
                self._bt_selected_device_key = ""
                self.render_bluetooth_console(v2, devices, adapters)
                return

            adapter_names = {
                adapter.get("id"): f"Adapter {chr(65 + index)}"
                for index, adapter in enumerate(adapters)
            }
            for device in devices:
                status = "Connected" if device.get("connected") else ("Paired" if device.get("paired") else "Available")
                legacy_status = "[CONNECTED]" if device.get("connected") else ("[PAIRED]" if device.get("paired") else "[FOUND]")
                role = device.get("kind") or device.get("type") or "unknown"
                adapter_id = device.get("adapter_id") or ""
                adapter_label = adapter_names.get(adapter_id, adapter_id or "adapter?")
                mac = device.get("address") or device.get("mac", "")
                key = device.get("key") or device.get("device_key") or ""
                rssi = self.bt_rssi(device)
                label = f"{legacy_status} {device.get('name', 'Unknown')} | {adapter_label} | {rssi} | {status} | {role} | {mac}"
                bt_list.add_option(label)
                self._bt_mac_by_prompt[label] = mac
                self._bt_target_by_prompt[label] = {
                    "adapter_id": adapter_id,
                    "device_key": key,
                    "mac": mac,
                }
            selected_key = getattr(self, "_bt_selected_device_key", "")
            selected_index = next(
                (
                    index
                    for index in range(bt_list.option_count)
                    if self._bt_target_by_prompt.get(str(bt_list.get_option_at_index(index).prompt), {}).get("device_key")
                    == selected_key
                ),
                0,
            )
            bt_list.highlighted = selected_index
            selected_prompt = str(bt_list.get_option_at_index(selected_index).prompt)
            self._bt_selected_device_key = self._bt_target_by_prompt[selected_prompt].get("device_key", "")
            self.render_bluetooth_console(v2, devices, adapters)
        except Exception as e:
            self.write_log(f"[WARN] Exception: {e}")

    def bt_rssi(self, device: dict | None) -> str:
        value = (device or {}).get("rssi")
        return f"{value} dBm" if isinstance(value, int | float) else "-- dBm"

    def bt_status(self, device: dict | None) -> str:
        device = device or {}
        if device.get("connected"):
            return "[green]Connected[/]"
        if device.get("paired"):
            return "[cyan]Paired[/]"
        if device.get("present") is False:
            return "[red]Absent[/]"
        return "[yellow]Available[/]"

    def bt_adapter_devices(self, devices: list[dict], adapter_id: str | None) -> list[dict]:
        return [device for device in devices if (device.get("adapter_id") or "") == (adapter_id or "")]

    def bt_avg_rssi(self, devices: list[dict]) -> str:
        values: list[float] = []
        for device in devices:
            value = device.get("rssi")
            if isinstance(value, int | float):
                values.append(float(value))
        if not values:
            return "--"
        return str(round(sum(values) / len(values)))

    def render_bluetooth_console(self, state: dict | None, devices: list[dict], adapters: list[dict]) -> None:
        console_state = dict(state or {})
        console_state["devices"] = devices
        console_state["adapters"] = adapters
        console_state["selected_device_key"] = getattr(self, "_bt_selected_device_key", "")
        cpu_percent, memory_percent = self.bluetooth_system_metrics()
        view = build_bluetooth_console(
            console_state,
            facts=self.bluetooth_system_facts(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            language=self.language,
        )
        self._bluetooth_console_view = view
        panels = {
            "#txt_bt_header": view.header,
            "#txt_bluetooth_topology": view.topology,
            "#txt_bt_legend": view.legend,
            "#txt_bluetooth_adapter_a": view.adapter_a,
            "#txt_bluetooth_adapter_b": view.adapter_b,
            "#txt_bluetooth_available": view.available,
            "#txt_bluetooth_actions": view.actions,
            "#txt_bt_adapter_status": view.adapter_status,
            "#txt_bt_diagnostics": view.diagnostics,
            "#txt_bt_events": view.recent_events,
            "#txt_bt_help": view.help,
            "#txt_bt_footer": view.footer,
            "#txt_bt_compact": view.compact,
        }
        for selector, content in panels.items():
            self.set_static_text(selector, content)
        self.apply_bluetooth_layout(self.size.width, self.size.height)

    def bluetooth_system_facts(self) -> dict[str, str]:
        """Return cached, low-cost system labels for the Bluetooth diagnostics."""
        cached = getattr(self, "_bluetooth_system_facts", None)
        if cached is not None:
            return cached
        os_label = "Linux"
        try:
            values = {}
            with open("/etc/os-release") as handle:
                for line in handle:
                    if "=" in line:
                        key, value = line.rstrip().split("=", 1)
                        values[key] = value.strip('"')
            os_label = values.get("VERSION_CODENAME") or values.get("PRETTY_NAME") or os_label
            if os.uname().machine in {"aarch64", "arm64"}:
                os_label += " (64-bit)"
        except OSError:
            pass
        try:
            with open("/proc/uptime") as handle:
                uptime_seconds = int(float(handle.read().split()[0]))
            days, remainder = divmod(uptime_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes = remainder // 60
            uptime = f"{days}d {hours}h {minutes}m"
        except (OSError, ValueError, IndexError):
            uptime = "--"
        self._bluetooth_system_facts = {
            "os": os_label,
            "kernel": os.uname().release,
            "bluez": "bluez-dbus",
            "uptime": uptime,
        }
        return self._bluetooth_system_facts

    def bluetooth_system_metrics(self) -> tuple[float | None, float | None]:
        """Return lightweight CPU load and memory utilization percentages."""
        try:
            cpu_count = os.cpu_count() or 1
            cpu_percent = min(100.0, os.getloadavg()[0] / cpu_count * 100.0)
        except OSError:
            cpu_percent = None
        try:
            memory = {}
            with open("/proc/meminfo") as handle:
                for line in handle:
                    key, value, *_ = line.split()
                    if key in {"MemTotal:", "MemAvailable:"}:
                        memory[key] = int(value)
            memory_percent = 100.0 * (1.0 - memory["MemAvailable:"] / memory["MemTotal:"])
        except (OSError, KeyError, ValueError, ZeroDivisionError):
            memory_percent = None
        return cpu_percent, memory_percent

    def apply_bluetooth_layout(self, width: int, height: int) -> None:
        """Select the full reference layout or the compact low-resolution fallback."""
        try:
            panel = self.query_one("#panel_bluetooth")
            panel.set_class(width < 170 or height < 38, "bt-compact")
        except Exception:
            pass

    def on_resize(self, event: events.Resize) -> None:
        self.apply_bluetooth_layout(event.size.width, event.size.height)

    def render_bluetooth_topology(self, adapter_a: dict, adapter_b: dict, devices_a: list[dict], devices_b: list[dict]) -> str:
        def device_rows(items: list[dict], color: str) -> list[str]:
            rows = []
            for device in items[:4]:
                name = str(device.get("name") or "Unknown Device")[:18]
                rows.append(f"[{color}]|--[/] {name:<18} {self.bt_rssi(device):>8}")
            return rows or [f"[{color}]|--[/] No devices"]

        left = device_rows(devices_a, "cyan")
        right = device_rows(devices_b, "green")
        while len(left) < 4:
            left.append("")
        while len(right) < 4:
            right.append("")
        a_power = "[green]Powered On[/]" if adapter_a.get("powered") else "[red]Powered Off[/]"
        b_power = "[green]Powered On[/]" if adapter_b.get("powered") else "[red]Powered Off[/]"
        lines = [
            "[cyan]TOPOLOGY[/]  RPi Bluetooth Control Center (TUI)    Dual Adapter Management    Auto Connect: [green]ON[/]    [S] Scan All  [P] Pair New  [R] Refresh",
            "",
            f"        [cyan]ADAPTER A[/] {a_power:<22} RSSI Avg: {self.bt_avg_rssi(devices_a):>4} dBm"
            f"                              [green]ADAPTER B[/] {b_power:<22} RSSI Avg: {self.bt_avg_rssi(devices_b):>4} dBm",
            f"{left[0]:<44}     [cyan]  /\\  [/]" + "      DENS-MTB      " + f"[green]  /\\  [/]{right[0]:>34}",
            f"{left[1]:<44}     [cyan] < BT >[/] --- [red]x[/] --- [green]< BT >[/] {right[1]:>34}",
            f"{left[2]:<44}     [cyan]  \\/  [/]" + "  [red]Connection Error[/]  " + f"[green]  \\/  [/]{right[2]:>28}",
            f"{left[3]:<44}              Out of Range                  {right[3]:>34}",
            "",
            f"        [cyan]{len([d for d in devices_a if d.get('connected')])} Connected[/]  {len([d for d in devices_a if not d.get('connected')])} Available"
            f"                                      [green]{len([d for d in devices_b if d.get('connected')])} Connected[/]  {len([d for d in devices_b if not d.get('connected')])} Available",
        ]
        return "\n".join(lines)

    def render_bluetooth_table(self, title: str, adapter: dict, devices: list[dict], color: str) -> str:
        rows = [f"[{color}]{title}[/]", "#  Device Name          RSSI      Status", "------------------------------------------"]
        for index, device in enumerate(devices[:5], start=1):
            name = str(device.get("name") or "Unknown Device")[:18]
            rows.append(f"{index:<2} {name:<18} {self.bt_rssi(device):>8}  {self.bt_status(device)}")
        if not devices:
            rows.append("No devices reported")
        rows.append("")
        rows.append(f"Adapter Address: {adapter.get('address', '--')}")
        return "\n".join(rows)

    def render_bluetooth_available(self, devices: list[dict]) -> str:
        rows = ["[yellow]AVAILABLE DEVICES[/]", "Device Name          RSSI      Adapter", "--------------------------------------"]
        available = [device for device in devices if not device.get("connected")][:5]
        for device in available:
            adapter = device.get("adapter_id") or "-"
            rows.append(f"{str(device.get('name') or 'Unknown')[:18]:<18} {self.bt_rssi(device):>8}  {adapter[:8]}")
        if not available:
            rows.append("No available devices")
        rows.append("")
        rows.append("Press [P] to pair selected device")
        return "\n".join(rows)

    def render_bluetooth_actions(self) -> str:
        return "\n".join(
            [
                "[magenta]QUICK ACTIONS[/]",
                "[S] Scan All Adapters",
                "[P] Pair New Device",
                "[C] Connect to Device",
                "[D] Disconnect Device",
                "[R] Refresh Topology",
                "[X] Remove Paired Device",
                "[M] More Settings",
            ]
        )

    def render_bluetooth_adapters(self, state: dict | None) -> None:
        if not state:
            self.set_static_text("#txt_bluetooth_adapters", "")
            return
        backend = state.get("backend") or {}
        adapters = state.get("adapters") or []
        lines = [
            f"Backend: {backend.get('name', 'unknown')}"
            f"{' degraded' if backend.get('degraded') else ''}"
        ]
        if not adapters:
            lines.append("Adapters: none present")
        for adapter in adapters[:3]:
            power = "on" if adapter.get("powered") else "off"
            scan = "scan" if adapter.get("discovering") else "idle"
            present = "present" if adapter.get("present") else "absent"
            role = adapter.get("role") or "-"
            index = adapter.get("index")
            index_text = "?" if index is None else str(index)
            lines.append(
                f"{adapter.get('alias') or adapter.get('name') or adapter.get('id')}: "
                f"{present}, power:{power}, {scan}, hci{index_text}, "
                f"role:{role}, addr:{adapter.get('address', '?')}"
            )
        self.set_static_text("#txt_bluetooth_adapters", "\n".join(lines))

    def render_bluetooth_soundbar(self, state: dict | None) -> None:
        readiness = ((state or {}).get("diagnostics") or {}).get("soundbar")
        if not readiness:
            self.set_static_text("#txt_bluetooth_soundbar", "")
            return
        steps = readiness.get("steps") or []
        parts = []
        for step in steps[:8]:
            value = step.get("state")
            status = "OK" if value is True else ("BLOCK" if value is False else "UNK")
            parts.append(f"{status}:{step.get('id')}")
        self.set_static_text(
            "#txt_bluetooth_soundbar",
            "[bold]Soundbar[/bold]: " + (" -> ".join(parts) if parts else "unknown"),
        )

    def render_bluetooth_controller(self, controller: dict | None) -> None:
        if not controller:
            self.set_static_text("#txt_bluetooth_controller", "")
            return
        ready = self.tr("bt_controller_ready") if controller.get("ready") else self.tr("bt_controller_not_ready")
        modules = controller.get("modules") or {}
        driver = "xpadneo" if modules.get("xpadneo") else ("uhid" if modules.get("uhid") else ("xpad" if modules.get("xpad") else "missing"))
        ertm = controller.get("ertm") or {}
        ertm_value = "yes" if ertm.get("disabled") is True else ("no" if ertm.get("disabled") is False else "unknown")
        inputs = controller.get("input_devices") or []
        steamlink = (controller.get("steamlink") or {}).get("available")
        blockers = controller.get("blockers") or []
        controller_count = len(controller.get("controllers") or controller.get("connected") or [])
        text = (
            f"[bold]{self.tr('bt_controller_title')}[/bold]: {ready}\n"
            f"Controllers: {controller_count} | ERTM disabled: {ertm_value} | Driver: {driver}\n"
            f"Input: {', '.join(inputs) if inputs else 'unknown'} | Steam Link: {'available' if steamlink is True else ('missing' if steamlink is False else 'unknown')}"
        )
        if blockers:
            text += "\nBlockers: " + "; ".join(blockers[:3])
        self.set_static_text("#txt_bluetooth_controller", text)

    def render_bluetooth_events(self, state: dict | None) -> None:
        if not state:
            self.set_static_text("#txt_bluetooth_events", "")
            return
        rows = []
        for operation in (state.get("operations") or [])[-3:]:
            rows.append(f"OP {operation.get('type')} {operation.get('state')}")
        for event in (state.get("events") or [])[-3:]:
            rows.append(f"{event.get('type')}: {event.get('message')}")
        self.set_static_text("#txt_bluetooth_events", "\n".join(rows))

    async def update_wifi_hotspot_info(self) -> None:
        """Read hotspot and raspotify settings and status."""
        try:
            ssid_out = await self.run_sys_cmd("grep -m1 '^ssid=' /etc/hostapd/rpi-service.conf | cut -d'=' -f2")
            ssid = ssid_out if ssid_out else "RPi-service"
            hidden = "skryta" if self.language == "cz" else "hidden"
            self.query_one("#txt_hotspot_ssid", Static).update(f"Hotspot SSID: [bold]{ssid}[/] ({hidden})")
            
            leases = await self.run_sys_cmd("cat /var/lib/misc/dnsmasq.leases 2>/dev/null | wc -l")
            client_count = leases if leases else "0"
            clients = "Pripojeni klienti" if self.language == "cz" else "Connected clients"
            self.query_one("#txt_hotspot_clients", Static).update(f"{clients}: [bold]{client_count}[/]")
            
            hotspot_active = await self.run_sys_cmd("systemctl is-active hostapd")
            self.query_one("#switch_hotspot", Switch).value = (hotspot_active == "active")
            
            raspotify_active = await self.run_sys_cmd("systemctl is-active raspotify")
            self.query_one("#switch_raspotify", Switch).value = (raspotify_active == "active")
        except Exception as e:
            self.write_log(f"[WARN] Exception: {e}")

    async def restart_padlna(self) -> None:
        """Restart the pa-dlna background streaming client."""
        self.write_log("[SYSTEM] Restarting pa-dlna service...")
        await self.run_sys_cmd("systemctl --user restart pa-dlna || pkill -f pa-dlna")
        self.write_log("[SYSTEM] pa-dlna service restarted.")
        await self.update_audio_sinks()

    async def scan_bluetooth(self) -> None:
        """Scan for Bluetooth devices in background."""
        self.write_log("[BLUETOOTH] Starting discovery for 5s...")
        result = await asyncio.to_thread(devices_service.bluetooth_scan_devices, 5)
        if not result.get("ok"):
            self.write_log(f"[BLUETOOTH] Scan failed: {result.get('error', 'unknown error')}")
        self.write_log("[BLUETOOTH] Discovery complete.")
        await self.update_bluetooth_devices()

    async def run_bluetooth_action(self, action: str) -> None:
        try:
            bt_list = self.query_one("#list_bluetooth_devices", OptionList)
            if bt_list.highlighted is not None:
                option = bt_list.get_option_at_index(bt_list.highlighted)
                prompt = str(option.prompt)
                if prompt in {t("cz", "no_bt"), t("en", "no_bt")}: return
                target = getattr(self, "_bt_target_by_prompt", {}).get(prompt, {})
                mac = target.get("mac") or getattr(self, "_bt_mac_by_prompt", {}).get(prompt)
                if not mac and "(" in prompt and ")" in prompt:
                    mac = prompt.split("(")[-1].strip(")")
                if mac:
                    self.write_log(f"[BLUETOOTH] {action.capitalize()} for {mac}...")
                    adapter_id = target.get("adapter_id")
                    device_key = target.get("device_key")
                    if adapter_id and device_key:
                        from rpi_dashboard.services.bluetooth import service as bt_service
                        result = await asyncio.to_thread(
                            bt_service.device_action,
                            action,
                            adapter_id=adapter_id,
                            device_key=device_key,
                            mac=mac,
                        )
                    else:
                        runner = getattr(devices_service, f"bluetooth_{action}")
                        result = await asyncio.to_thread(runner, mac)
                    self.write_log(f"[BLUETOOTH] Result: {result.get('result') or result.get('error') or result.get('output')}")
                    if action in ["connect", "disconnect"]:
                        await self.update_audio_sinks()
                    await self.update_bluetooth_devices()
        except Exception as e:
            self.write_log(f"[ERROR] Bluetooth {action} failed: {e}")

    def selected_bluetooth_target(self) -> dict:
        """Return the adapter-scoped target behind the highlighted device row."""
        bt_list = self.query_one("#list_bluetooth_devices", OptionList)
        if bt_list.highlighted is None:
            return {}
        prompt = str(bt_list.get_option_at_index(bt_list.highlighted).prompt)
        return dict(getattr(self, "_bt_target_by_prompt", {}).get(prompt, {}))

    async def run_bluetooth_file_send(self) -> None:
        """Send the newest Downloads file after a deliberate second key press."""
        from rpi_dashboard.services.bluetooth import service as bt_service

        target = self.selected_bluetooth_target()
        if not target.get("adapter_id") or not target.get("device_key"):
            self.show_bluetooth_notice("Select an adapter-scoped Bluetooth device first.")
            return
        candidates = await asyncio.to_thread(bt_service.download_files)
        files = candidates.get("files") or []
        if not files:
            self.show_bluetooth_notice("No eligible regular file exists in ~/Downloads.")
            return
        newest = files[0]
        confirmation = (newest["path"], target["device_key"])
        if getattr(self, "_bt_pending_file_send", None) != confirmation:
            self._bt_pending_file_send = confirmation
            self.show_bluetooth_notice(
                f"Press F again to send {newest['name']} to the selected trusted device."
            )
            return
        self._bt_pending_file_send = None
        result = await asyncio.to_thread(
            bt_service.send_file,
            newest["path"],
            adapter_id=target["adapter_id"],
            device_key=target["device_key"],
            mac=target.get("mac"),
        )
        self.show_bluetooth_notice(
            "Transfer started."
            if result.get("ok")
            else f"Transfer failed: {result.get('error', 'unknown error')}"
        )
        await self.update_bluetooth_devices()

    async def cancel_latest_bluetooth_transfer(self) -> None:
        """Cancel the newest active OBEX transfer visible in the shared snapshot."""
        from rpi_dashboard.services.bluetooth import service as bt_service

        state = getattr(self, "_bluetooth_state_snapshot", {})
        transfers = (state.get("obex") or {}).get("transfers") or []
        active = [
            item
            for item in transfers
            if item.get("status") in {"queued", "starting", "active"}
        ]
        if not active:
            self.show_bluetooth_notice("No active Bluetooth file transfer.")
            return
        result = await asyncio.to_thread(
            bt_service.cancel_file_transfer,
            active[-1].get("id", ""),
        )
        self.show_bluetooth_notice(
            "Transfer cancelled."
            if result.get("ok")
            else f"Cancel failed: {result.get('error', 'unknown error')}"
        )
        await self.update_bluetooth_devices()

    async def run_bluetooth_media_action(self, action: str) -> None:
        """Run one capability-checked AVRCP action for the selected device."""
        from rpi_dashboard.services.bluetooth import service as bt_service

        target = self.selected_bluetooth_target()
        if not target.get("adapter_id") or not target.get("device_key"):
            self.show_bluetooth_notice("Select an AVRCP-capable Bluetooth device first.")
            return
        result = await asyncio.to_thread(
            bt_service.media_action,
            action,
            adapter_id=target["adapter_id"],
            device_key=target["device_key"],
            mac=target.get("mac"),
        )
        self.show_bluetooth_notice(
            f"Media {action} sent."
            if result.get("ok")
            else f"Media action failed: {result.get('error', 'unknown error')}"
        )
        await self.update_bluetooth_devices()

    async def scan_wifi(self) -> None:
        self.write_log("[WIFI] Scanning available networks...")
        out = await self.run_sys_cmd("nmcli -t -f SSID dev wifi")
        wifi_list = self.query_one("#list_wifi_networks", OptionList)
        wifi_list.clear_options()
        if out:
            seen = set()
            for line in out.splitlines():
                ssid = line.strip()
                if ssid and ssid not in seen:
                    seen.add(ssid)
                    wifi_list.add_option(ssid)
        if not wifi_list.option_count:
             wifi_list.add_option(self.empty_wifi_label())
        self.write_log("[WIFI] Scan complete.")

    async def connect_wifi(self) -> None:
        try:
            wifi_list = self.query_one("#list_wifi_networks", OptionList)
            if wifi_list.highlighted is not None:
                option = wifi_list.get_option_at_index(wifi_list.highlighted)
                ssid = str(option.prompt)
                if ssid in {t("cz", "no_wifi"), t("en", "no_wifi")}: return
                pwd_input = self.query_one("#input_wifi_password", Input)
                pwd = pwd_input.value.strip()
                self.write_log(f"[WIFI] Connecting to {ssid}...")
                if pwd:
                    cmd = f"nmcli dev wifi connect {shlex.quote(ssid)} password {shlex.quote(pwd)}"
                else:
                    cmd = f"nmcli dev wifi connect {shlex.quote(ssid)}"
                out = await self.run_sys_cmd(cmd)
                self.write_log(f"[WIFI] {out.strip()}")
                pwd_input.value = ""
        except Exception as e:
            self.write_log(f"[ERROR] Wi-Fi connection failed: {e}")

    async def disconnect_all_bluetooth(self) -> None:
        """Disconnect all connected Bluetooth audio devices."""
        self.write_log("[BLUETOOTH] Disconnecting all Bluetooth devices...")
        state = await asyncio.to_thread(devices_service.devices_state)
        connected_devices = [d for d in state.get("bluetooth", {}).get("paired", []) if d.get("connected")]
        for d in connected_devices:
            mac = d.get("mac")
            if mac:
                await asyncio.to_thread(devices_service.bluetooth_disconnect, mac)
        self.write_log("[BLUETOOTH] Disconnect complete.")
        await self.update_bluetooth_devices()

    async def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle toggles for the rescue Wi-Fi hotspot and Raspotify service."""
        if getattr(self, "_updating_settings", False):
            return
        if event.switch.id == "switch_hotspot":
            action = "start" if event.value else "stop"
            self.write_log(f"[SYSTEM] Setting rescue hotspot: {action}")
            await self.run_sys_cmd(f"sudo -n systemctl {action} hostapd dnsmasq")
        elif event.switch.id == "switch_raspotify":
            action = "start" if event.value else "stop"
            self.write_log(f"[SYSTEM] Setting Spotify Connect (raspotify): {action}")
            await self.run_sys_cmd(f"sudo -n systemctl {action} raspotify")
        elif event.switch.id == "switch_alexa_bt":
            action = "start" if event.value else "stop"
            self.write_log(f"[AUDIO] Setting Alexa AUX -> BT loopback: {action}")
            import webserver
            try:
                res = webserver.audio_route_alexa_bt(action)
                self.write_log(f"[AUDIO] Alexa Loopback {action}: {res}")
            except Exception as e:
                self.write_log(f"[ERROR] Alexa Loopback failed: {e}")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle selection of default audio sink in OptionList."""
        if event.option_list.id == "list_audio_sinks":
            selected_text = str(event.option.prompt)
            sink_id = getattr(self, "_audio_sink_by_prompt", {}).get(selected_text)
            if sink_id:
                self.write_log(f"[AUDIO] Setting default audio output to: {sink_id}")
                asyncio.create_task(self.set_audio_sink(sink_id))
        elif event.option_list.id == "list_bluetooth_devices":
            prompt = str(event.option.prompt)
            self._bt_selected_device_key = self._bt_target_by_prompt.get(prompt, {}).get("device_key", "")
            self.render_bluetooth_console(
                getattr(self, "_bluetooth_state_snapshot", {}),
                getattr(self, "_bluetooth_devices_snapshot", []),
                getattr(self, "_bluetooth_adapters_snapshot", []),
            )

    async def set_audio_sink(self, sink_id: str) -> None:
        """Sets default PulseAudio/PipeWire audio sink and refreshes list."""
        await self.run_sys_cmd(f"pactl set-default-sink {shlex.quote(sink_id)}")
        await self.update_audio_sinks()

    async def on_unmount(self) -> None:
        """Clean up background tasks and close the API server."""
        if hasattr(self, "api_runner") and self.api_runner:
            await self.api_runner.cleanup()
        legacy_server = getattr(self, "_legacy_webserver", None)
        if legacy_server is not None:
            await asyncio.to_thread(legacy_server.shutdown)
            legacy_server.server_close()
        legacy_thread = getattr(self, "_legacy_webserver_thread", None)
        if legacy_thread is not None:
            legacy_thread.join(timeout=5)

    async def start_api_server(self) -> None:
        """Start the aiohttp API listener in the background with CORS and auth middlewares."""
        await asyncio.to_thread(self._start_legacy_webserver)

        @web.middleware
        async def _middleware(request, handler):
            return await self.api_middleware(request, handler)

        api_app = web.Application(middlewares=[_middleware])
        
        # Register all routes
        api_app.router.add_post("/play", self.handle_play)
        api_app.router.add_get("/status", self.handle_status)
        api_app.router.add_post("/player/pause", self.handle_player_pause)
        api_app.router.add_post("/player/stop", self.handle_player_stop)
        api_app.router.add_post("/player/volume", self.handle_player_volume)
        api_app.router.add_post("/player/seek", self.handle_player_seek)
        api_app.router.add_get("/audio/sinks", self.handle_audio_get_sinks)
        api_app.router.add_post("/audio/sinks/select", self.handle_audio_select_sink)
        api_app.router.add_get("/bluetooth/devices", self.handle_bluetooth_get_devices)
        api_app.router.add_post("/bluetooth/connect", self.handle_bluetooth_connect)
        api_app.router.add_get("/wifi/networks", self.handle_wifi_get_networks)
        api_app.router.add_post("/wifi/connect", self.handle_wifi_connect)
        api_app.router.add_post("/system/reboot", self.handle_system_reboot)
        # api_app.router.add_post("/system/screensaver", self.handle_system_screensaver)
        api_app.router.add_post("/mode/launch", self.handle_mode_launch)
        api_app.router.add_post("/mode/stop", self.handle_mode_stop)
        api_app.router.add_get("/", self.handle_webui_index)
        api_app.router.add_get("/index.html", self.handle_webui_index)
        api_app.router.add_get("/manifest.json", self.handle_webui_manifest)
        api_app.router.add_get("/favicon.ico", self.handle_webui_favicon)
        api_app.router.add_static("/static", self.static_dir())
        api_app.router.add_route("*", "/mpv/play", self.handle_legacy_mpv_play)
        api_app.router.add_route("*", "/mpv/stop", self.handle_legacy_mpv_stop)
        api_app.router.add_route("*", "/mpv/status", self.handle_legacy_mpv_status)
        api_app.router.add_route("*", "/mpv/seek", self.handle_legacy_mpv_seek)
        api_app.router.add_route("*", "/mpv/volume", self.handle_registered_api_route)
        api_app.router.add_route("*", "/mpv/memory", self.handle_mpv_memory)
        api_app.router.add_route("*", "/mpv/memory/clear", self.handle_mpv_memory_clear)
        api_app.router.add_route("*", "/mpv/memory-save", self.handle_mpv_memory_save)
        api_app.router.add_route("*", "/mpv/toggle", self.handle_mpv_toggle)
        api_app.router.add_route("*", "/mpv/vol", self.handle_mpv_relative_volume)
        api_app.router.add_route("*", "/mpv/seekabs", self.handle_mpv_seek_absolute)
        api_app.router.add_route("*", "/bt/state", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/discovery", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/adapter-power", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/device-action", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/device-autoconnect", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/scan", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/controller", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/pair", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/trust", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/connect", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/disconnect", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/remove", self.handle_registered_api_route)
        api_app.router.add_route("*", "/audio/multi-output", self.handle_registered_api_route)
        api_app.router.add_route("*", "/audio/bluetooth-profiles", self.handle_registered_api_route)
        api_app.router.add_route("*", "/audio/mute-state", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/device-profile", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/transfers", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/files", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/file-send", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/file-cancel", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/operation", self.handle_registered_api_route)
        api_app.router.add_route("*", "/bt/media", self.handle_registered_api_route)
        api_app.router.add_route("*", "/devices/state", self.handle_registered_api_route)
        api_app.router.add_route("*", "/{tail:.*}", self.handle_legacy_webserver_proxy)

        self.api_runner = web.AppRunner(api_app)
        await self.api_runner.setup()
        self.api_site = web.TCPSite(self.api_runner, "0.0.0.0", API_PORT)
        try:
            await self.api_site.start()
            self.write_log(f"[NETWORK] API server listening on 0.0.0.0:{API_PORT} with CORS and Auth enabled")
        except Exception as e:
            self.write_log(f"[ERROR] Failed to start API server: {e}")

    def _start_legacy_webserver(self) -> None:
        """Start an internal compatibility server for legacy WebUI endpoints."""
        if getattr(self, "_legacy_webserver", None) is not None:
            return
        import webserver

        server = ThreadingHTTPServer(("127.0.0.1", 0), webserver.H)
        thread = threading.Thread(
            target=server.serve_forever,
            name="legacy-webui-compat",
            daemon=True,
        )
        thread.start()
        self._legacy_webserver = server
        self._legacy_webserver_thread = thread

    async def handle_legacy_webserver_proxy(self, request: web.Request) -> web.Response:
        """Proxy unported routes to the complete legacy WebUI compatibility handler."""
        server = getattr(self, "_legacy_webserver", None)
        if server is None:
            raise web.HTTPServiceUnavailable(text="Legacy WebUI compatibility server unavailable")
        body = await request.read()
        url = f"http://127.0.0.1:{server.server_port}{request.path_qs}"

        def proxy_request() -> tuple[int, bytes, str]:
            headers = {}
            if request.content_type:
                headers["Content-Type"] = request.content_type
            proxied = urllib.request.Request(
                url,
                data=body if request.method in {"POST", "PUT", "PATCH"} else None,
                headers=headers,
                method=request.method,
            )
            try:
                with urllib.request.urlopen(proxied, timeout=30) as response:
                    return (
                        response.status,
                        response.read(),
                        response.headers.get("Content-Type", "application/json"),
                    )
            except urllib.error.HTTPError as exc:
                return (
                    exc.code,
                    exc.read(),
                    exc.headers.get("Content-Type", "application/json"),
                )

        status, payload, content_type = await asyncio.to_thread(proxy_request)
        return web.Response(status=status, body=payload, headers={"Content-Type": content_type})

    def static_dir(self) -> str:
        """Return the static WebUI asset directory."""
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "rpi_dashboard", "static")

    async def handle_webui_index(self, request: web.Request) -> web.StreamResponse:
        """Serve the browser WebUI from the live TUI service."""
        index_path = os.path.join(self.static_dir(), "index.html")
        return web.FileResponse(index_path)

    async def handle_webui_manifest(self, request: web.Request) -> web.Response:
        """Serve a minimal PWA manifest compatible with the legacy webserver."""
        manifest = {
            "name": "RPi Dashboard",
            "short_name": "RPiDash",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#0d1117",
            "theme_color": "#0d1117",
            "icons": [
                {
                    "src": (
                        "data:image/svg+xml,<svg xmlns=\"http://www.w3.org/2000/svg\" "
                        "viewBox=\"0 0 100 100\"><rect width=\"100\" height=\"100\" "
                        "rx=\"20\" fill=\"%23238636\"/><text x=\"50\" y=\"50\" "
                        "font-size=\"50\" text-anchor=\"middle\" dy=\".3em\" "
                        "fill=\"white\">TV</text></svg>"
                    ),
                    "sizes": "192x192 512x512",
                    "type": "image/svg+xml",
                }
            ],
            "share_target": {
                "action": "/",
                "method": "GET",
                "params": {"title": "title", "text": "text", "url": "share_url"},
            },
        }
        return web.json_response(manifest, content_type="application/manifest+json")

    async def handle_webui_favicon(self, request: web.Request) -> web.Response:
        """Avoid noisy browser favicon 404s."""
        return web.Response(status=204, content_type="image/x-icon")

    async def handle_legacy_mpv_play(self, request: web.Request) -> web.Response:
        """Start mpv through the legacy WebUI playback path."""
        import webserver

        url = request.query.get("url", "").strip()
        quality = request.query.get("q")
        resume = request.query.get("resume", "0") not in {"0", "", "false", "False"}
        if not url:
            return web.json_response({"error": "no url"}, status=400)
        result = await asyncio.to_thread(webserver.mpv_start, url, quality, resume)
        if result.get("ok"):
            self._legacy_mpv_started_at = time.time()
        return web.json_response(result)

    async def handle_legacy_mpv_stop(self, request: web.Request) -> web.Response:
        """Stop mpv through the legacy WebUI playback path."""
        import webserver

        memory = await asyncio.to_thread(webserver.save_mpv_resume_memory) if webserver.mpv_ipc_socket_live() else None
        stopped = await asyncio.to_thread(webserver.mpv_stop)
        self._legacy_mpv_started_at = 0.0
        return web.json_response({"ok": True, "memory": memory, "stop": stopped})

    async def handle_legacy_mpv_status(self, request: web.Request) -> web.Response:
        """Return legacy mpv status shape expected by the WebUI."""
        import webserver

        result = await asyncio.to_thread(webserver.mpv_st)
        if result.get("on") and not result.get("pos") and getattr(self, "_legacy_mpv_started_at", None):
            result["pos"] = max(0.1, time.time() - self._legacy_mpv_started_at)
        return web.json_response(result)

    async def handle_legacy_mpv_seek(self, request: web.Request) -> web.Response:
        """Relative seek endpoint used by the WebUI buttons."""
        import webserver

        try:
            delta = float(request.query.get("d", "10"))
        except ValueError:
            return web.json_response({"ok": False, "error": "d must be number"})
        await asyncio.to_thread(webserver.mcmd, "seek", delta, "relative")
        return web.json_response({"ok": True})

    async def handle_mpv_memory(self, request: web.Request) -> web.Response:
        """Return saved resume memory for WebUI compatibility."""
        import webserver

        url = request.query.get("url", "")
        if not url:
            return web.json_response({"error": "no url"}, status=400)
        memory = await asyncio.to_thread(webserver.get_mpv_memory_for_url, url)
        return web.json_response({"ok": True, "memory": memory})

    async def handle_mpv_memory_clear(self, request: web.Request) -> web.Response:
        """Accept resume-memory clear requests without breaking playback."""
        import webserver

        url = request.query.get("url", "")
        cleared = await asyncio.to_thread(webserver.clear_mpv_memory_for_url, url) if url else False
        return web.json_response({"ok": True, "cleared": cleared})

    async def handle_mpv_memory_save(self, request: web.Request) -> web.Response:
        """Save mpv resume memory when mpv is active."""
        import webserver

        if not await asyncio.to_thread(webserver.mpv_ipc_socket_live):
            return web.json_response({"ok": True, "memory": "mpv not running"})
        memory = await asyncio.to_thread(webserver.save_mpv_resume_memory)
        return web.json_response({"ok": True, "memory": memory})

    async def handle_mpv_toggle(self, request: web.Request) -> web.Response:
        """Toggle mpv pause for WebUI compatibility."""
        import webserver

        await asyncio.to_thread(webserver.mcmd, "cycle", "pause")
        status = await asyncio.to_thread(webserver.mget, "pause")
        return web.json_response({"ok": True, "paused": status.get("data", False)})

    async def handle_mpv_relative_volume(self, request: web.Request) -> web.Response:
        """Adjust mpv volume relatively for keyboard/WebUI controls."""
        import webserver

        try:
            delta = int(request.query.get("d", "10"))
        except ValueError:
            return web.json_response({"ok": False, "error": "d must be integer"})
        await asyncio.to_thread(webserver.mcmd, "add", "volume", delta)
        return web.json_response({"ok": True})

    async def handle_mpv_seek_absolute(self, request: web.Request) -> web.Response:
        """Seek mpv to an absolute position for the WebUI scrubber."""
        import webserver

        try:
            position = float(request.query.get("pos", "0"))
        except ValueError:
            return web.json_response({"ok": False, "error": "pos must be number"})
        await asyncio.to_thread(webserver.mcmd, "seek", position, "absolute")
        return web.json_response({"ok": True})

    async def handle_registered_api_route(self, request: web.Request) -> web.Response:
        """Serve shared API route handlers from the live TUI API process."""
        handler = get_route(request.path)
        if handler is None:
            raise web.HTTPNotFound()
        query = {key: [value] for key, value in request.query.items()}
        if request.method in {"POST", "PUT", "PATCH"}:
            body_query = await self.request_body_query(request)
            query.update(body_query)
        result = await asyncio.to_thread(handler, query)
        return web.json_response(result)

    async def request_body_query(self, request: web.Request) -> dict[str, list[str]]:
        """Normalize JSON or form bodies into the legacy handler query shape."""
        try:
            if request.content_type == "application/json":
                data = await request.json()
            else:
                data = dict(await request.post())
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(key): [str(value)] for key, value in data.items()}

    async def api_middleware(self, request: web.Request, handler) -> web.Response:
        """Middleware to handle CORS and optional API Key validation."""
        try:
            if request.method == "OPTIONS":
                response = web.Response(status=204)
                self.add_cors_headers(response)
                return response

            # API Key authorization (X-API-Key header or query parameter)
            api_key = os.getenv("API_KEY")
            if api_key:
                req_key = request.headers.get("X-API-Key") or request.query.get("api_key")
                if req_key != api_key:
                    response = web.json_response({"status": "error", "message": "Unauthorized"}, status=401)
                    self.add_cors_headers(response)
                    return response

            try:
                response = await handler(request)
            except web.HTTPException as ex:
                response = ex
            except Exception as e:
                import traceback
                with open("/tmp/api_error.log", "a") as f:
                    f.write("INNER Exception in api_middleware:\n")
                    traceback.print_exc(file=f)
                response = web.json_response({"status": "error", "message": str(e)}, status=500)
                
            self.add_cors_headers(response)
            return response
        except Exception as e:
            import traceback
            with open("/tmp/api_error.log", "a") as f:
                f.write("OUTER Exception in api_middleware:\n")
                traceback.print_exc(file=f)
            raise

    def add_cors_headers(self, response: web.Response) -> None:
        """Inject CORS headers into aiohttp response."""
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"

    async def handle_play(self, request: web.Request) -> web.Response:
        """Route to cast/play a URL. Rejects with 409 if a mode is already active."""
        if self.mode_switcher.state != ModeSwitcherState.IDLE:
            return web.json_response(
                {"status": "error", "message": f"Conflict: switcher is currently in state {self.mode_switcher.state.name}"},
                status=409
            )
        try:
            data = await request.json()
            url = data.get("url")
            if not url:
                return web.json_response({"status": "error", "message": "Missing 'url' key"}, status=400)
            asyncio.create_task(self.play_media(url))
            return web.json_response({"status": "ok", "message": "Play request accepted"})
        except Exception as e:
            return web.json_response({"status": "error", "message": f"Malformed JSON: {e}"}, status=400)

    async def handle_status(self, request: web.Request) -> web.Response:
        """Route to query telemetry, active mode, and screensaver state."""
        try:
            mode_status = self.query_one("#mode_status", ModeStatus)
            stats_widget = self.query_one(SystemStats)
            ram_used, ram_total = stats_widget.get_ram_usage()
            
            status_data = {
                "status": "ok",
                "mode": mode_status.current_mode,
                                "system": {
                    "cpu_usage_pct": round(stats_widget.get_cpu_usage(), 1),
                    "ram_used_gb": round(ram_used, 2),
                    "ram_total_gb": round(ram_total, 2),
                    "cpu_temp_c": round(stats_widget.get_cpu_temp(), 1),
                    "ip": stats_widget.get_local_ip()
                }
            }
            return web.json_response(status_data)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def send_mpv_ipc(self, command: list) -> bool:
        """Send JSON command to running MPV instance via unix socket."""
        try:
            reader, writer = await asyncio.open_unix_connection("/tmp/mpv-socket")
            import json
            payload = json.dumps({"command": command}) + "\n"
            writer.write(payload.encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return True
        except Exception as e:
            return False

    async def handle_player_pause(self, request: web.Request) -> web.Response:
        """Route to pause/resume MPV."""
        success = await self.send_mpv_ipc(["cycle", "pause"])
        if success:
            return web.json_response({"status": "ok", "message": "Pause toggled"})
        return web.json_response({"status": "error", "message": "Player not active or IPC failed"}, status=400)

    async def handle_player_stop(self, request: web.Request) -> web.Response:
        """Route to stop active MPV playback and restore dashboard."""
        if hasattr(self, "mode_switcher") and self.mode_switcher.active_process:
            self.write_log("[API] Remote request to stop playback.")
            asyncio.create_task(self.mode_switcher._teardown_active_process())
            return web.json_response({"status": "ok", "message": "Playback stop initiated"})
        return web.json_response({"status": "error", "message": "No active playback process"}, status=400)

    async def handle_player_volume(self, request: web.Request) -> web.Response:
        """Route to set player/system volume."""
        try:
            data = await request.json()
            level = data.get("level")
            if level is None or not (0 <= level <= 100):
                return web.json_response({"status": "error", "message": "Invalid volume level (0-100)"}, status=400)
            
            # Set default system volume (pactl)
            await self.run_sys_cmd(f"pactl set-sink-volume @DEFAULT_SINK@ {level}%")
            # Also try MPV IPC volume
            await self.send_mpv_ipc(["set_property", "volume", level])
            
            return web.json_response({"status": "ok", "message": f"Volume set to {level}%"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=400)

    async def handle_player_seek(self, request: web.Request) -> web.Response:
        """Route to seek MPV playback (seconds can be positive or negative)."""
        try:
            data = await request.json()
            seconds = data.get("seconds")
            if seconds is None:
                return web.json_response({"status": "error", "message": "Missing 'seconds' parameter"}, status=400)
            success = await self.send_mpv_ipc(["seek", seconds])
            if success:
                return web.json_response({"status": "ok", "message": f"Seeked {seconds}s"})
            return web.json_response({"status": "error", "message": "Player not active or IPC failed"}, status=400)
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=400)

    async def handle_audio_get_sinks(self, request: web.Request) -> web.Response:
        """Route to get list of PulseAudio/PipeWire audio sinks."""
        try:
            default_sink = await self.run_sys_cmd("pactl get-default-sink")
            sinks_out = await self.run_sys_cmd("pactl list short sinks")
            sinks = []
            if sinks_out:
                for line in sinks_out.split("\n"):
                    parts = line.split()
                    if len(parts) >= 2:
                        sink_id = parts[1]
                        sinks.append({
                            "sink_id": sink_id,
                            "active": (sink_id == default_sink)
                        })
            return web.json_response({"status": "ok", "sinks": sinks})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_audio_select_sink(self, request: web.Request) -> web.Response:
        """Route to set default audio sink."""
        try:
            data = await request.json()
            sink_id = data.get("sink_id")
            if not sink_id:
                return web.json_response({"status": "error", "message": "Missing 'sink_id'"}, status=400)
            await self.set_audio_sink(sink_id)
            return web.json_response({"status": "ok", "message": f"Default sink set to {sink_id}"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=400)

    async def handle_bluetooth_get_devices(self, request: web.Request) -> web.Response:
        """Route to list paired and connected Bluetooth devices."""
        try:
            state = await asyncio.to_thread(devices_service.devices_state)
            bluetooth = state.get("bluetooth", {})
            devices = bluetooth.get("paired", [])
            
            paired = [
                f"{d['name']} ({d['mac']})" for d in devices if d.get("paired")
            ]
            connected = [
                f"{d['name']} ({d['mac']})" for d in devices if d.get("connected")
            ]
            
            return web.json_response({"status": "ok", "paired": paired, "connected": connected})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_bluetooth_connect(self, request: web.Request) -> web.Response:
        """Route to connect/disconnect Bluetooth devices."""
        try:
            data = await request.json()
            mac = data.get("mac")
            action = data.get("action", "connect") # connect, disconnect, pair, remove, trust
            if not mac:
                return web.json_response({"status": "error", "message": "Missing 'mac' address"}, status=400)
            
            if action not in ["connect", "disconnect", "pair", "remove", "trust"]:
                return web.json_response({"status": "error", "message": "Invalid action"}, status=400)
                
            runner = getattr(devices_service, f"bluetooth_{action}")
            res = await asyncio.to_thread(runner, mac)
            return web.json_response({"status": "ok", "message": f"Action {action} dispatched", "output": res.get("output", "")})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=400)

    async def handle_wifi_get_networks(self, request: web.Request) -> web.Response:
        """Route to scan and return available Wi-Fi access points."""
        try:
            wifi_out = await self.run_sys_cmd("nmcli -t -f SSID,SIGNAL,SECURITY device wifi list")
            networks = []
            if wifi_out:
                for line in wifi_out.split("\n"):
                    if line.strip():
                        parts = line.split(":")
                        if len(parts) >= 2:
                            networks.append({
                                "ssid": parts[0],
                                "signal": parts[1],
                                "security": parts[2] if len(parts) > 2 else ""
                            })
            return web.json_response({"status": "ok", "networks": networks})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_wifi_connect(self, request: web.Request) -> web.Response:
        """Route to connect to a Wi-Fi network."""
        try:
            data = await request.json()
            ssid = data.get("ssid")
            password = data.get("password")
            if not ssid:
                return web.json_response({"status": "error", "message": "Missing 'ssid'"}, status=400)
            
            cmd = f"nmcli device wifi connect {shlex.quote(ssid)}"
            if password:
                cmd += f" password {shlex.quote(password)}"
                
            res = await self.run_sys_cmd(cmd)
            return web.json_response({"status": "ok", "message": "Connection command dispatched", "output": res})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=400)

    async def handle_system_reboot(self, request: web.Request) -> web.Response:
        """Route to safely reboot the host system."""
        self.write_log("[SYSTEM] Remote request to reboot system received.")
        asyncio.create_task(self.run_sys_cmd("sudo -n reboot"))
        return web.json_response({"status": "ok", "message": "Reboot command sent"})

    async def handle_mode_launch(self, request: web.Request) -> web.Response:
        """Launch a mode from Web UI."""
        try:
            data = await request.json()
            mode = data.get("mode", "")
            modes = {
                "steamlink": (["steamlink"], False),
                "gfn": (["cage", "-d", "--", "moonlight-qt", "stream", "192.168.0.67", "GeForce Now"], False),
                "mpv": (["mpv", "--vo=drm"], False),
                "spotify": (["cage", "-d", "--", "cog", "--platform=drm", "https://open.spotify.com"], False),
                "amazon": (["cage", "-d", "--", "chromium-browser", "--kiosk", "--autoplay-policy=no-user-gesture-required", "https://music.amazon.com"], False),
            }
            if mode not in modes:
                return web.json_response({"error": f"Unknown mode: {mode}"}, status=400)
            cmd, use_suspend = modes[mode]
            self.write_log(f"[NETWORK] Launching mode: {mode} via Web UI")
            asyncio.create_task(self.launch_mode(mode.upper(), cmd, use_suspend=use_suspend))
            return web.json_response({"status": "ok", "mode": mode})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_mode_stop(self, request: web.Request) -> web.Response:
        """Stop the currently running mode/app."""
        try:
            if hasattr(self, "mode_switcher") and self.mode_switcher.active_process:
                self.write_log("[NETWORK] Stopping active mode via Web UI")
                await self.mode_switcher._teardown_active_process()
                return web.json_response({"status": "ok", "message": "Mode stopped"})
            else:
                return web.json_response({"status": "ok", "message": "No active mode to stop"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)


    async def play_media(self, url: str) -> None:
        """Suspend TUI, play the URL using mpv (with IPC socket), and resume TUI using ModeSwitcher.
        
        RPi 3B+ uses /etc/mpv/mpv.conf for H.264-only format selection and HW decode settings.
        """
        mode_status = self.query_one("#mode_status", ModeStatus)
        mode_status.current_mode = "MPV (Player)"
        self.write_log(f"[NETWORK] Playing cast URL: {url}")
        
        from mode_switcher import MPV_TIMEOUT
        import subprocess as _sp
        # Force HDMI connector active for DRM output (RPi 3B+ quirk)
        try:
            with open("/sys/class/drm/card0-HDMI-A-1/status", "w") as f:
                f.write("on")
        except Exception as e:
            self.write_log(f"[WARN] Exception: {e}")
        # Blank console so DRM planes are not overridden by fbcon
        try:
            _sp.run(["sudo", "bash", "-c",
                     "echo 1 > /sys/class/vt/console/dkblnk 2>/dev/null;"
                     "cat /dev/zero > /dev/fb0 2>/dev/null"],
                    timeout=2, capture_output=True)
        except Exception as e:
            self.write_log(f"[WARN] Exception: {e}")
        # MPV reads settings from /etc/mpv/mpv.conf (H.264-only, v4l2m2m HW decode)
        # use_suspend=False: DRM/KMS video output breaks when TUI suspends
        await self.mode_switcher.launch([
            "mpv", "--vo=drm", "--hwdec=auto", "--fs",
            "--input-ipc-server=/tmp/mpv-socket", url
        ], timeout=MPV_TIMEOUT, use_suspend=False)
        # Restore console after MPV finishes
        try:
            _sp.run(["sudo", "bash", "-c",
                     "echo 0 > /sys/class/vt/console/dkblnk 2>/dev/null"],
                    timeout=2, capture_output=True)
        except Exception as e:
            self.write_log(f"[WARN] Exception: {e}")
        
        mode_status.current_mode = "IDLE (Dashboard)"
        self.write_log("[SYSTEM] Finished media playback. Dashboard restored.")


    def move_bluetooth_selection(self, delta: int) -> None:
        """Move the hidden action target and mirror it in the visible tables."""
        bt_list = self.query_one("#list_bluetooth_devices", OptionList)
        if bt_list.option_count == 0:
            return
        current = bt_list.highlighted if bt_list.highlighted is not None else 0
        selected_index = (current + delta) % bt_list.option_count
        bt_list.highlighted = selected_index
        prompt = str(bt_list.get_option_at_index(selected_index).prompt)
        self._bt_selected_device_key = self._bt_target_by_prompt.get(prompt, {}).get("device_key", "")
        self.render_bluetooth_console(
            getattr(self, "_bluetooth_state_snapshot", {}),
            getattr(self, "_bluetooth_devices_snapshot", []),
            getattr(self, "_bluetooth_adapters_snapshot", []),
        )

    def on_key(self, event) -> None:
        """Reset inactivity on any keyboard input and handle test hotkeys."""
        try:
            bluetooth_active = self.query_one(TabbedContent).active == "tab_bluetooth"
        except Exception:
            bluetooth_active = False
        if bluetooth_active and event.key in {"up", "down"}:
            event.stop()
            self.move_bluetooth_selection(-1 if event.key == "up" else 1)
        elif bluetooth_active and event.key in {"space", "left_square_bracket", "right_square_bracket"}:
            event.stop()
            action = {
                "left_square_bracket": "previous",
                "right_square_bracket": "next",
            }.get(event.key)
            if action is None:
                selected_key = getattr(self, "_bt_selected_device_key", "")
                media = (
                    (getattr(self, "_bluetooth_state_snapshot", {}).get("diagnostics") or {}).get("media")
                    or {}
                )
                player = next(
                    (
                        item
                        for item in media.get("players") or []
                        if item.get("device_key") == selected_key
                    ),
                    {},
                )
                action = "pause" if player.get("status") == "playing" else "play"
            asyncio.create_task(self.run_bluetooth_media_action(action))
        elif bluetooth_active and event.key in {"s", "p", "t", "c", "d", "r", "x", "g", "m", "f", "k", "q"}:
            event.stop()
            if event.key == "s":
                asyncio.create_task(self.scan_bluetooth())
            elif event.key in {"p", "t", "c", "d", "x"}:
                action = {
                    "p": "pair",
                    "t": "trust",
                    "c": "connect",
                    "d": "disconnect",
                    "x": "remove",
                }[event.key]
                asyncio.create_task(self.run_bluetooth_action(action))
            elif event.key == "r":
                asyncio.create_task(self.update_bluetooth_devices())
            elif event.key == "g":
                self.show_bluetooth_notice("Adapter priority is planned; no adapter state was changed.")
            elif event.key == "m":
                self.show_bluetooth_notice("More settings are available in the WebUI Expert mode.")
            elif event.key == "f":
                asyncio.create_task(self.run_bluetooth_file_send())
            elif event.key == "k":
                asyncio.create_task(self.cancel_latest_bluetooth_transfer())
            elif event.key == "q":
                self.exit()
        elif event.key == "w":
            asyncio.create_task(self.run_watchdog_test())
        elif event.key == "c":
            asyncio.create_task(self.run_crash_test())
        elif event.key == "g":
            asyncio.create_task(self.run_concurrency_test())

    def show_bluetooth_notice(self, message: str) -> None:
        """Show a visible status for intentionally unavailable Bluetooth commands."""
        self.set_static_text("#txt_bt_footer", f"[yellow]NOTICE:[/] {message}")
        view = getattr(self, "_bluetooth_console_view", None)
        if view is not None:
            compact_rows = view.compact.splitlines()
            notice = f"[yellow]NOTICE:[/] {message}"
            try:
                compact_rows[compact_rows.index("")] = notice
            except ValueError:
                compact_rows[-1] = notice
            self.set_static_text("#txt_bt_compact", "\n".join(compact_rows))
        self.write_log(f"[BLUETOOTH] {message}")


    async def run_watchdog_test(self) -> None:
        """Runs a watchdog timeout test: sleep 999 with 5s timeout."""
        self.write_log("[TEST] Starting watchdog test (sleep 999 with 5s timeout)...")
        await self.mode_switcher.launch(["sleep", "999"], timeout=5)

    async def run_crash_test(self) -> None:
        """Runs a crash recovery test: exit 1 (false)."""
        self.write_log("[TEST] Starting crash recovery test (false)...")
        await self.mode_switcher.launch(["false"], timeout=0)

    async def run_concurrency_test(self) -> None:
        """Runs a concurrency serialization test (two rapid launch calls, second waits)."""
        self.write_log("[TEST] Starting concurrency serialization test...")
        t1 = asyncio.create_task(self.mode_switcher.launch(["sleep", "2"], timeout=0))
        await asyncio.sleep(0.1)
        t2 = asyncio.create_task(self.mode_switcher.launch(["sleep", "2"], timeout=0))
        results = await asyncio.gather(t1, t2)
        # Both should succeed (serialized execution)
        assert all(results), f"Expected both to succeed, got {results}"
        self.write_log("[TEST] Concurrency serialization test passed - both launches succeeded.")

    MIN_FREE_RAM_MB = {
        "STEAM LINK":             100,
        "GEFORCE NOW (Moonlight)": 150,
        "MPV (Player)":            150,
        "SPOTIFY (WPE WebKit)":    200,
        "AMAZON MUSIC (Chromium)": 350,
    }

    def _free_ram_mb(self) -> int:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) // 1024
        except Exception as e:
            self.write_log(f"[WARN] Exception: {e}")
        return 9999  # optimistic fallback

    async def launch_mode(self, mode_name: str, command: list[str], timeout: float = 0, use_suspend: bool = True) -> None:
        """Helper to transition states, launch external app via switcher, and restore TUI."""
        needed = self.MIN_FREE_RAM_MB.get(mode_name, 100)
        free = self._free_ram_mb()
        if free < needed:
            self.write_log(f"[REFUSED] {mode_name} needs {needed}MB free, only {free}MB available.")
            mode_status = self.query_one("#mode_status", ModeStatus)
            original = mode_status.current_mode
            mode_status.current_mode = f"REFUSED: low RAM ({free}MB/{needed}MB)"
            await asyncio.sleep(3)
            mode_status.current_mode = original
            return

        mode_status = self.query_one("#mode_status", ModeStatus)
        mode_status.current_mode = mode_name
        self.write_log(f"[SYSTEM] Activating mode: {mode_name}")
        if mode_name == "TERMINAL (tmux)":
            self.write_log(self.tr("terminal_help"))
        else:
            self.write_log(self.tr("app_help"))
        
        await self.mode_switcher.launch(command, timeout=timeout, use_suspend=use_suspend)
        
        mode_status.current_mode = "IDLE (Dashboard)"
        self.write_log(f"[SYSTEM] Mode {mode_name} terminated. Dashboard restored.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Reset inactivity on button presses and handle mode changes via ModeSwitcher."""
        import shutil
        
        if event.button.id == "btn_lang_cz":
            self.language = "cz"
            self.apply_language()
            return

        if event.button.id == "btn_lang_en":
            self.language = "en"
            self.apply_language()
            return

        if event.button.id == "btn_steamlink":
            test_command = os.getenv("RPIDASHBOARD_TEST_COMMAND")
            cmd = shlex.split(test_command) if test_command else ["steamlink"]
            is_fallback = False
            if not test_command and not shutil.which("steamlink"):
                self.write_log("[SYSTEM] 'steamlink' not found, falling back to 'nano' for TTY test.")
                cmd = ["nano"]
                is_fallback = True
            asyncio.create_task(self.launch_mode("STEAM LINK", cmd, timeout=0, use_suspend=is_fallback))
            
        elif event.button.id == "btn_gfn":
            cmd = ["cage", "-d", "--", "moonlight-qt", "stream", "192.168.0.67", "GeForce Now"]
            is_fallback = False
            if not shutil.which("cage") or not shutil.which("moonlight-qt"):
                self.write_log("[SYSTEM] 'cage' or 'moonlight-qt' not found, falling back to 'nano' for TTY test.")
                cmd = ["nano"]
                is_fallback = True
            asyncio.create_task(self.launch_mode("GEFORCE NOW (Moonlight)", cmd, timeout=0, use_suspend=is_fallback))
            
        elif event.button.id == "btn_mpv":
            try:
                url_input = self.query_one("#input_mpv_url", Input)
                url = url_input.value.strip()
            except Exception as e:
                url = ""
            
            if not url:
                self.write_log("[ERROR] MPV: No URL provided. Enter a YouTube URL or direct media link.")
                return
            
            # Use play_media which properly launches MPV with IPC socket
            asyncio.create_task(self.play_media(url))
            
        elif event.button.id == "btn_spotify":
            cmd = ["cage", "-d", "--", "cog", "--platform=drm", "https://open.spotify.com"]
            is_fallback = False
            if not shutil.which("cage") or not shutil.which("cog"):
                self.write_log("[SYSTEM] 'cage' or 'cog' (WPE WebKit) not found, falling back to 'top' for visual test.")
                cmd = ["top"]
                is_fallback = True
            asyncio.create_task(self.launch_mode("SPOTIFY (WPE WebKit)", cmd, timeout=0, use_suspend=is_fallback))
            
        elif event.button.id == "btn_amazon":
            cmd = ["cage", "-d", "--", "chromium", "--kiosk", "--autoplay-policy=no-user-gesture-required", "--disable-gpu", "--single-process", "--memory-pressure-off", "https://music.amazon.com"]
            is_fallback = False
            if not shutil.which("cage") or not shutil.which("chromium"):
                self.write_log("[SYSTEM] 'chromium' not found, falling back to 'top' for visual test.")
                cmd = ["top"]
                is_fallback = True
            asyncio.create_task(self.launch_mode("AMAZON MUSIC (Chromium)", cmd, timeout=0, use_suspend=is_fallback))
            
        elif event.button.id == "btn_stop":
            if hasattr(self, "mode_switcher") and self.mode_switcher.active_process:
                asyncio.create_task(self.mode_switcher._teardown_active_process())
                
        elif event.button.id == "btn_restart_padlna":
            asyncio.create_task(self.restart_padlna())
            
        elif event.button.id == "btn_scan_bluetooth":
            asyncio.create_task(self.scan_bluetooth())
        elif event.button.id == "btn_pair_bluetooth":
            asyncio.create_task(self.run_bluetooth_action("pair"))
        elif event.button.id == "btn_trust_bluetooth":
            asyncio.create_task(self.run_bluetooth_action("trust"))
        elif event.button.id == "btn_connect_bluetooth":
            asyncio.create_task(self.run_bluetooth_action("connect"))
        elif event.button.id == "btn_remove_bluetooth":
            asyncio.create_task(self.run_bluetooth_action("remove"))

        elif event.button.id == "btn_disconnect_bluetooth":
            asyncio.create_task(self.disconnect_all_bluetooth())

        elif event.button.id == "btn_scan_wifi":
            asyncio.create_task(self.scan_wifi())
        elif event.button.id == "btn_connect_wifi":
            asyncio.create_task(self.connect_wifi())

        elif event.button.id == "btn_vol_down":
            self.write_log("[AUDIO] Decreasing volume by 10%")
            asyncio.create_task(self.run_sys_cmd("pactl set-sink-volume @DEFAULT_SINK@ -10%"))
            asyncio.create_task(self.update_audio_sinks())

        elif event.button.id == "btn_vol_up":
            self.write_log("[AUDIO] Increasing volume by 10%")
            asyncio.create_task(self.run_sys_cmd("pactl set-sink-volume @DEFAULT_SINK@ +10%"))
            asyncio.create_task(self.update_audio_sinks())

        elif event.button.id == "btn_save_latency":
            try:
                val_str = self.query_one("#input_dlna_latency", Input).value.strip()
                val = int(val_str)
            except Exception as e:
                self.write_log("[ERROR] Invalid latency value. Enter an integer.")
            else:
                self.write_log(f"[AUDIO] Saving DLNA latency: {val} ms")
                import webserver
                try:
                    res = webserver.audio_set_latency("dlna_output_offset_ms", val)
                    self.write_log(f"[AUDIO] Latency saved: {res}")
                except Exception as e:
                    self.write_log(f"[ERROR] Saving latency failed: {e}")

        elif event.button.id == "btn_terminal":
            cmd = ["tmux", "new-session", "-A", "-s", "RPi"]
            asyncio.create_task(self.launch_mode("TERMINAL (tmux)", cmd, timeout=0, use_suspend=True))

if __name__ == "__main__":
    import sys as _sys

    if "--headless" in _sys.argv:
        # Headless mode: run only the aiohttp API server without the TUI.
        # Useful for automated testing in environments without a terminal.
        async def _run_headless() -> None:
            # CORS middleware for headless
            @web.middleware
            async def _cors_middleware(request, handler):
                if request.method == "OPTIONS":
                    resp = web.Response(status=204)
                else:
                    try:
                        resp = await handler(request)
                    except Exception as e:
                        resp = web.json_response({"status": "error", "message": str(e)}, status=500)
                resp.headers["Access-Control-Allow-Origin"] = "*"
                resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
                resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"
                return resp

            api_app = web.Application(middlewares=[_cors_middleware])

            async def _play(req):
                try:
                    data = await req.json()
                    url = data.get("url")
                    if not url:
                        return web.json_response({"status": "error", "message": "Missing 'url' key"}, status=400)
                    return web.json_response({"status": "ok", "message": "Play request accepted"})
                except Exception as exc:
                    return web.json_response({"status": "error", "message": f"Malformed request: {exc}"}, status=400)

            async def _status(req):
                return web.json_response({
                    "status": "ok",
                    "mode": "IDLE (Dashboard)",
                                        "system": {
                        "cpu_usage_pct": 10.0,
                        "ram_used_gb": 0.5,
                        "ram_total_gb": 1.0,
                        "cpu_temp_c": 45.0,
                        "ip": "127.0.0.1"
                    }
                })

            async def _player_pause(req):
                return web.json_response({"status": "ok", "message": "Pause toggled"})

            async def _player_stop(req):
                return web.json_response({"status": "ok", "message": "Playback stop initiated"})

            async def _player_volume(req):
                return web.json_response({"status": "ok", "message": "Volume set"})

            async def _player_seek(req):
                return web.json_response({"status": "ok", "message": "Seeked"})

            async def _audio_sinks(req):
                return web.json_response({
                    "status": "ok",
                    "sinks": [{"sink_id": "alsa_output.platform-3f902000.hdmi.hdmi-stereo", "active": True}]
                })

            async def _audio_select(req):
                return web.json_response({"status": "ok", "message": "Sink set"})

            async def _bluetooth_devices(req):
                return web.json_response({"status": "ok", "paired": [], "connected": []})

            async def _bluetooth_connect(req):
                return web.json_response({"status": "ok", "message": "Connected"})

            async def _wifi_networks(req):
                return web.json_response({"status": "ok", "networks": []})

            async def _wifi_connect(req):
                return web.json_response({"status": "ok", "message": "Connected"})

            async def _system_reboot(req):
                return web.json_response({"status": "ok", "message": "Rebooting"})


            api_app.router.add_post("/play", _play)
            api_app.router.add_get("/status", _status)
            api_app.router.add_post("/player/pause", _player_pause)
            api_app.router.add_post("/player/stop", _player_stop)
            api_app.router.add_post("/player/volume", _player_volume)
            api_app.router.add_post("/player/seek", _player_seek)
            api_app.router.add_get("/audio/sinks", _audio_sinks)
            api_app.router.add_post("/audio/sinks/select", _audio_select)
            api_app.router.add_get("/bluetooth/devices", _bluetooth_devices)
            api_app.router.add_post("/bluetooth/connect", _bluetooth_connect)
            api_app.router.add_get("/wifi/networks", _wifi_networks)
            api_app.router.add_post("/wifi/connect", _wifi_connect)
            api_app.router.add_post("/system/reboot", _system_reboot)
            runner = web.AppRunner(api_app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", API_PORT)
            await site.start()
            print(f"HEADLESS: API server listening on port {API_PORT}", flush=True)
            try:
                # Run until cancelled
                while True:
                    await asyncio.sleep(3600)
            except asyncio.CancelledError:
                pass
            finally:
                await runner.cleanup()

        try:
            asyncio.run(_run_headless())
        except KeyboardInterrupt:
            pass
    else:
        import signal as _signal

        app = RPiDashboard()
        _signal.signal(_signal.SIGTERM, lambda _signum, _frame: app.exit())
        app.run()
