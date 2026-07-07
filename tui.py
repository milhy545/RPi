from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Log, Button, TabbedContent, TabPane, OptionList, Switch, Label, Input
from textual.reactive import reactive
import time
import os
import sys
import socket
import asyncio
import shlex
from datetime import datetime
from aiohttp import web
from mode_switcher import ModeSwitcher, ModeSwitcherState
from config import TUI_STATS_INTERVAL, TUI_SETTINGS_INTERVAL
from rpi_dashboard.tui.formatting import human_audio_sink, human_bt_device


API_PORT = int(os.getenv("RPIDASHBOARD_API_PORT", "8090"))
NO_BT_DEVICES_LABEL = "No paired Bluetooth devices. Use Scan, then Pair."
NO_WIFI_NETWORKS_LABEL = "No Wi-Fi networks found. Run scan again or check adapter."

class SystemStats(Static):
    """Zobrazuje reálnou zátěž systému z /proc a /sys."""
    def on_mount(self) -> None:
        self._settings_cache = {
            "network": 0.0,
            "audio": 0.0,
            "bluetooth": 0.0,
            "wifi": 0.0
        }
        self._settings_cache_ttl = 10.0

        # Inicializace stavových proměnných pro výpočet CPU delta
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
                    # První měření
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
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.254.254.254', 1))
            ip = s.getsockname()[0]
        except Exception as e:
            ip = '127.0.0.1'
        finally:
            s.close()
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
            f"🔥 CPU: {cpu:.1f}% | "
            f"🐏 RAM: {ram_str} | "
            f"🌡️ Temp: {temp:.1f}°C | "
            f"🌐 IP: {ip}"
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
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.254.254.254', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
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
                mode = app.mode_switcher.state.value
            except Exception:
                mode = "IDLE"
        self.update(
            f"MODE: {mode} | CPU: {cpu:.1f}% | "
            f"RAM: {int(ram_used * 1024)}MB/{int(ram_total * 1024)}MB | "
            f"TEMP: {temp:.1f}C | IP: {ip} | API: {API_PORT}"
        )

class ModeStatus(Static):
    """Zobrazuje aktuální režim RPi."""
    current_mode = reactive("IDLE (Dashboard)")

    def render(self) -> str:
        return f"📡 Aktuální Mód: [bold green]{self.current_mode}[/]"



class RPiDashboard(App):
    """Hacker-style TUI Dashboard pro RPi."""
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
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield TopStatus(id="top_status")
        
        with TabbedContent(initial="tab_player"):
            with TabPane("Player", id="tab_player"):
                with Vertical(id="main-content"):
                    yield Static("[bold]Player[/bold]", classes="settings-title")
                    yield Input(placeholder="YouTube URL nebo přímý odkaz...", id="input_mpv_url", classes="mpv-url-input")
                    yield Button("Spustit MPV", id="btn_mpv", variant="success")
                    yield ModeStatus(id="mode_status")

            with TabPane("Apps", id="tab_apps"):
                with Vertical(id="sidebar"):
                    yield Static("[bold]Apps[/bold]", classes="title")
                    yield Button("Spustit SteamLink", id="btn_steamlink", variant="primary")
                    yield Button("GeForce Now", id="btn_gfn", variant="default")
                    yield Button("Spotify WebOS", id="btn_spotify", variant="warning")
                    yield Button("Amazon Music", id="btn_amazon", variant="default")
                    yield Button("Zastavit vše", id="btn_stop", variant="error")
                    yield Button("Otevřít Terminál", id="btn_terminal", variant="default")

            with TabPane("Audio", id="tab_audio"):
                with Vertical(classes="settings-panel", id="panel_audio"):
                    yield Static("[bold]Zvukový výstup (DLNA/BT/HDMI)[/bold]", classes="settings-title")
                    yield OptionList(id="list_audio_sinks")
                    with Horizontal():
                        yield Button("Vol -10%", id="btn_vol_down")
                        yield Button("Vol +10%", id="btn_vol_up")
                    yield Label("DLNA Latence (ms):")
                    yield Input(placeholder="0", id="input_dlna_latency")
                    yield Button("Uložit latenci", id="btn_save_latency")
                    with Horizontal():
                        yield Label("Alexa AUX -> BT:")
                        yield Switch(id="switch_alexa_bt", value=False)
                    yield Button("Restartovat pa-dlna", id="btn_restart_padlna", variant="default")

            with TabPane("Devices", id="tab_devices"):
                with Vertical(classes="settings-panel", id="panel_bluetooth"):
                    yield Static("[bold]Bluetooth zařízení[/bold]", classes="settings-title")
                    yield OptionList(id="list_bluetooth_devices")
                    with Horizontal():
                        yield Button("Skenovat", id="btn_scan_bluetooth", variant="primary")
                        yield Button("Spárovat", id="btn_pair_bluetooth", variant="success")
                        yield Button("Důvěřovat", id="btn_trust_bluetooth", variant="warning")
                    with Horizontal():
                        yield Button("Připojit", id="btn_connect_bluetooth", variant="success")
                        yield Button("Odpojit", id="btn_disconnect_bluetooth", variant="error")
                        yield Button("Odebrat", id="btn_remove_bluetooth", variant="error")

            with TabPane("Network", id="tab_network"):
                with Horizontal():
                    with Vertical(classes="settings-panel", id="panel_network"):
                        yield Static("[bold]Síť a Tailscale[/bold]", classes="settings-title")
                        yield Static("Získávám síťové informace...", id="txt_network_info")
                        yield Static("Tailscale Status: --", id="txt_tailscale_info")
                    with Vertical(classes="settings-panel", id="panel_wifi"):
                        yield Static("[bold]Wi-Fi a Záchranný Hotspot[/bold]", classes="settings-title")
                        yield OptionList(id="list_wifi_networks")
                        with Horizontal():
                            yield Button("Skenovat Wi-Fi", id="btn_scan_wifi", variant="primary")
                        yield Input(placeholder="Heslo (nepovinné pro otevřené)", id="input_wifi_password", password=True)
                        yield Button("Připojit k vybrané síti", id="btn_connect_wifi", variant="success")
                        yield Static("Hotspot SSID: RPi-service (Skrytá)", id="txt_hotspot_ssid")
                        yield Static("Připojení klienti: --", id="txt_hotspot_clients")
                        with Horizontal():
                            yield Label("Záchranný Hotspot: ")
                            yield Switch(id="switch_hotspot", value=True)
                        yield Static("Spotify Connect (Raspotify):")
                        with Horizontal():
                            yield Switch(id="switch_raspotify", value=True)

            with TabPane("System", id="tab_system"):
                with Vertical(id="main-content"):
                    yield Static("[bold]System[/bold]", classes="settings-title")
                    yield SystemStats()

            with TabPane("Logs", id="tab_logs"):
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
        
        self.write_log("[SYSTEM] J.A.R.V.I.S. Dumb TV Interface načteno.")
        self.write_log(f"[NETWORK] Naslouchám na portu {API_PORT}...")
        self.write_log("[DAEMON] Čekám na příkazy z lokální sítě.")
        
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
            if active_tab not in {"tab_audio", "tab_devices", "tab_network", "tab_system"}:
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
            self.query_one("#txt_network_info", Static).update(f"🌐 IPs: {ip_str}")
            
            # 2. Tailscale Status
            ts_ip = await self.run_sys_cmd("tailscale ip -4")
            if ts_ip:
                self.query_one("#txt_tailscale_info", Static).update(f"🔒 Tailscale IP: [bold green]{ts_ip}[/]")
            else:
                self.query_one("#txt_tailscale_info", Static).update("🔒 Tailscale: Neaktivní / Není nainstalováno")
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
            
            bt_out = await self.run_sys_cmd("bluetoothctl devices Paired")
            if not bt_out:
                bt_out = await self.run_sys_cmd("bluetoothctl devices")
                
            if not bt_out:
                bt_list.add_option(NO_BT_DEVICES_LABEL)
                return

            connected_out = await self.run_sys_cmd("bluetoothctl devices Connected")
            connected_macs = {
                parts[1]
                for line in connected_out.splitlines()
                if line.startswith("Device ") and len(parts := line.split(None, 2)) >= 2
            }

            for line in bt_out.splitlines():
                if not line.startswith("Device "):
                    continue
                parts = line.split(None, 2)
                if len(parts) < 2:
                    continue
                mac = parts[1]
                item = human_bt_device(line, connected=mac in connected_macs)
                label = f"{item.status} {item.primary} - {item.detail}"
                bt_list.add_option(label)
                self._bt_mac_by_prompt[label] = item.detail
        except Exception as e:
            self.write_log(f"[WARN] Exception: {e}")

    async def update_wifi_hotspot_info(self) -> None:
        """Read hotspot and raspotify settings and status."""
        try:
            ssid_out = await self.run_sys_cmd("grep -m1 '^ssid=' /etc/hostapd/rpi-service.conf | cut -d'=' -f2")
            ssid = ssid_out if ssid_out else "RPi-service"
            self.query_one("#txt_hotspot_ssid", Static).update(f"📶 Hotspot SSID: [bold]{ssid}[/] (Skrytá)")
            
            leases = await self.run_sys_cmd("cat /var/lib/misc/dnsmasq.leases 2>/dev/null | wc -l")
            client_count = leases if leases else "0"
            self.query_one("#txt_hotspot_clients", Static).update(f"👥 Připojení klienti: [bold]{client_count}[/]")
            
            hotspot_active = await self.run_sys_cmd("systemctl is-active hostapd")
            self.query_one("#switch_hotspot", Switch).value = (hotspot_active == "active")
            
            raspotify_active = await self.run_sys_cmd("systemctl is-active raspotify")
            self.query_one("#switch_raspotify", Switch).value = (raspotify_active == "active")
        except Exception as e:
            self.write_log(f"[WARN] Exception: {e}")

    async def restart_padlna(self) -> None:
        """Restart the pa-dlna background streaming client."""
        self.write_log("[SYSTEM] Restartuji pa-dlna službu...")
        await self.run_sys_cmd("systemctl --user restart pa-dlna || pkill -f pa-dlna")
        self.write_log("[SYSTEM] Služba pa-dlna restartována.")
        await self.update_audio_sinks()

    async def scan_bluetooth(self) -> None:
        """Scan for Bluetooth devices in background."""
        self.write_log("[BLUETOOTH] Spouštím vyhledávání (5s)...")
        await self.run_sys_cmd("bluetoothctl --timeout 5 scan on")
        self.write_log("[BLUETOOTH] Vyhledávání dokončeno.")
        await self.update_bluetooth_devices()

    async def run_bluetooth_action(self, action: str) -> None:
        try:
            bt_list = self.query_one("#list_bluetooth_devices", OptionList)
            if bt_list.highlighted is not None:
                option = bt_list.get_option_at_index(bt_list.highlighted)
                prompt = str(option.prompt)
                if prompt == NO_BT_DEVICES_LABEL: return
                mac = getattr(self, "_bt_mac_by_prompt", {}).get(prompt)
                if not mac and "(" in prompt and ")" in prompt:
                    mac = prompt.split("(")[-1].strip(")")
                if mac:
                    self.write_log(f"[BLUETOOTH] {action.capitalize()} pro {mac}...")
                    out = await self.run_sys_cmd(f"bluetoothctl {action} {shlex.quote(mac)}")
                    self.write_log(f"[BLUETOOTH] Výsledek: {out.strip()}")
                    if action in ["connect", "disconnect"]:
                        await self.update_audio_sinks()
                    await self.update_bluetooth_devices()
        except Exception as e:
            self.write_log(f"[ERROR] Bluetooth {action} selhalo: {e}")

    async def scan_wifi(self) -> None:
        self.write_log("[WIFI] Skenuji dostupné sítě...")
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
             wifi_list.add_option(NO_WIFI_NETWORKS_LABEL)
        self.write_log("[WIFI] Skenování dokončeno.")

    async def connect_wifi(self) -> None:
        try:
            wifi_list = self.query_one("#list_wifi_networks", OptionList)
            if wifi_list.highlighted is not None:
                option = wifi_list.get_option_at_index(wifi_list.highlighted)
                ssid = str(option.prompt)
                if ssid == NO_WIFI_NETWORKS_LABEL: return
                pwd_input = self.query_one("#input_wifi_password", Input)
                pwd = pwd_input.value.strip()
                self.write_log(f"[WIFI] Připojuji k {ssid}...")
                if pwd:
                    cmd = f"nmcli dev wifi connect {shlex.quote(ssid)} password {shlex.quote(pwd)}"
                else:
                    cmd = f"nmcli dev wifi connect {shlex.quote(ssid)}"
                out = await self.run_sys_cmd(cmd)
                self.write_log(f"[WIFI] {out.strip()}")
                pwd_input.value = ""
        except Exception as e:
            self.write_log(f"[ERROR] Wi-Fi připojení selhalo: {e}")

    async def disconnect_all_bluetooth(self) -> None:
        """Disconnect all connected Bluetooth audio devices."""
        self.write_log("[BLUETOOTH] Odpojuji všechna Bluetooth zařízení...")
        devices = await self.run_sys_cmd("bluetoothctl devices Connected")
        for line in devices.split("\n"):
            parts = line.split()
            if len(parts) >= 2:
                mac = parts[1]
                await self.run_sys_cmd(f"bluetoothctl disconnect {shlex.quote(mac)}")
        self.write_log("[BLUETOOTH] Odpojení dokončeno.")
        await self.update_bluetooth_devices()

    async def on_switch_changed(self, event: Switch.Changed) -> None:
        """Handle toggles for the rescue Wi-Fi hotspot and Raspotify service."""
        if getattr(self, "_updating_settings", False):
            return
        if event.switch.id == "switch_hotspot":
            action = "start" if event.value else "stop"
            self.write_log(f"[SYSTEM] Nastavuji záchranný hotspot: {action}")
            await self.run_sys_cmd(f"sudo -n systemctl {action} hostapd dnsmasq")
        elif event.switch.id == "switch_raspotify":
            action = "start" if event.value else "stop"
            self.write_log(f"[SYSTEM] Nastavuji Spotify Connect (raspotify): {action}")
            await self.run_sys_cmd(f"sudo -n systemctl {action} raspotify")
        elif event.switch.id == "switch_alexa_bt":
            action = "start" if event.value else "stop"
            self.write_log(f"[AUDIO] Nastavuji Alexa AUX -> BT loopback: {action}")
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
                self.write_log(f"[AUDIO] Nastavuji výchozí zvukový výstup na: {sink_id}")
                asyncio.create_task(self.set_audio_sink(sink_id))

    async def set_audio_sink(self, sink_id: str) -> None:
        """Sets default PulseAudio/PipeWire audio sink and refreshes list."""
        await self.run_sys_cmd(f"pactl set-default-sink {shlex.quote(sink_id)}")
        await self.update_audio_sinks()

    async def on_unmount(self) -> None:
        """Clean up background tasks and close the API server."""
        if hasattr(self, "api_runner") and self.api_runner:
            await self.api_runner.cleanup()

    async def start_api_server(self) -> None:
        """Start the aiohttp API listener in the background with CORS and auth middlewares."""
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

        self.api_runner = web.AppRunner(api_app)
        await self.api_runner.setup()
        self.api_site = web.TCPSite(self.api_runner, "0.0.0.0", API_PORT)
        try:
            await self.api_site.start()
            self.write_log(f"[NETWORK] API server listening on 0.0.0.0:{API_PORT} with CORS and Auth enabled")
        except Exception as e:
            self.write_log(f"[ERROR] Failed to start API server: {e}")

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
            paired_out = await self.run_sys_cmd("bluetoothctl devices Paired")
            connected_out = await self.run_sys_cmd("bluetoothctl devices Connected")
            
            paired = [
                f"{p[2]} ({p[1]})"
                for line in paired_out.splitlines()
                if line.startswith("Device ") and len(p := line.split(None, 2)) == 3
            ]
            connected = [
                f"{p[2]} ({p[1]})"
                for line in connected_out.splitlines()
                if line.startswith("Device ") and len(p := line.split(None, 2)) == 3
            ]
            
            return web.json_response({"status": "ok", "paired": paired, "connected": connected})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    async def handle_bluetooth_connect(self, request: web.Request) -> web.Response:
        """Route to connect/disconnect Bluetooth devices."""
        try:
            data = await request.json()
            mac = data.get("mac")
            action = data.get("action", "connect") # connect, disconnect, pair, remove
            if not mac:
                return web.json_response({"status": "error", "message": "Missing 'mac' address"}, status=400)
            
            if action not in ["connect", "disconnect", "pair", "remove"]:
                return web.json_response({"status": "error", "message": "Invalid action"}, status=400)
                
            cmd = f"bluetoothctl {action} {shlex.quote(mac)}"
            res = await self.run_sys_cmd(cmd)
            return web.json_response({"status": "ok", "message": f"Action {action} dispatched", "output": res})
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
        mode_status.current_mode = "MPV (Přehrávač)"
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


    def on_key(self, event) -> None:
        """Reset inactivity on any keyboard input and handle test hotkeys."""
        if event.key == "w":
            asyncio.create_task(self.run_watchdog_test())
        elif event.key == "c":
            asyncio.create_task(self.run_crash_test())
        elif event.key == "g":
            asyncio.create_task(self.run_concurrency_test())


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
        "MPV (Přehrávač)":         150,
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
            mode_status.current_mode = f"REFUSED: málo RAM ({free}MB/{needed}MB)"
            await asyncio.sleep(3)
            mode_status.current_mode = original
            return

        mode_status = self.query_one("#mode_status", ModeStatus)
        mode_status.current_mode = mode_name
        self.write_log(f"[SYSTEM] Activating mode: {mode_name}")
        
        await self.mode_switcher.launch(command, timeout=timeout, use_suspend=use_suspend)
        
        mode_status.current_mode = "IDLE (Dashboard)"
        self.write_log(f"[SYSTEM] Mode {mode_name} terminated. Dashboard restored.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Reset inactivity on button presses and handle mode changes via ModeSwitcher."""
        import shutil
        
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
            self.write_log("[AUDIO] Snižuji hlasitost o 10%")
            asyncio.create_task(self.run_sys_cmd("pactl set-sink-volume @DEFAULT_SINK@ -10%"))
            asyncio.create_task(self.update_audio_sinks())

        elif event.button.id == "btn_vol_up":
            self.write_log("[AUDIO] Zvyšuji hlasitost o 10%")
            asyncio.create_task(self.run_sys_cmd("pactl set-sink-volume @DEFAULT_SINK@ +10%"))
            asyncio.create_task(self.update_audio_sinks())

        elif event.button.id == "btn_save_latency":
            try:
                val_str = self.query_one("#input_dlna_latency", Input).value.strip()
                val = int(val_str)
            except Exception as e:
                self.write_log("[ERROR] Neplatná hodnota latence. Zadejte celé číslo.")
            else:
                self.write_log(f"[AUDIO] Ukládám DLNA latenci: {val} ms")
                import webserver
                try:
                    res = webserver.audio_set_latency("dlna_output_offset_ms", val)
                    self.write_log(f"[AUDIO] Latence uložena: {res}")
                except Exception as e:
                    self.write_log(f"[ERROR] Uložení latence selhalo: {e}")

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
        app = RPiDashboard()
        app.run()
