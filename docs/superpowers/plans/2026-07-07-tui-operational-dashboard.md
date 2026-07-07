# TUI Operational Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the live `tui.py` TV dashboard into a professional, readable, task-oriented Textual operational dashboard while preserving existing mode switching and API behavior.

**Architecture:** Keep `tui.py` as the production entrypoint during the first iteration. Introduce focused helper functions and small Textual widgets in `rpi_dashboard/tui/` only where they reduce real duplication, then migrate `Audio` and `Devices` first because they are the current weak point. Use existing services and safe command wrappers instead of creating a second backend.

**Tech Stack:** Python 3.12, Textual, aiohttp, pytest, ruff, mypy, systemd on Raspberry Pi tty1.

---

## File Structure

- Modify `tui.py`: production entrypoint, layout composition, event handlers, and runtime integration.
- Create `rpi_dashboard/tui/formatting.py`: ASCII-safe labels, device/sink summarizers, badge strings, truncation helpers.
- Create `tests/test_tui_formatting.py`: unit coverage for labels, truncation, badges, and device summaries.
- Modify `tests/test_tui_modern.py`: layout coverage for the live `tui.py` path.
- Modify `AGENTS.md`: update handoff only after runtime verification.
- Do not replace `tui.py` with `rpi_dashboard/tui/modern.py` in this iteration.

## Task 1: Formatting Helpers For TV-Safe Labels

**Files:**
- Create: `rpi_dashboard/tui/formatting.py`
- Test: `tests/test_tui_formatting.py`

- [ ] **Step 1: Write failing tests**

```python
from rpi_dashboard.tui.formatting import (
    badge,
    human_audio_sink,
    human_bt_device,
    truncate_middle,
)


def test_badge_is_ascii_and_uppercase():
    assert badge("connected") == "[CONNECTED]"
    assert badge("active") == "[ACTIVE]"


def test_truncate_middle_keeps_both_ends():
    assert truncate_middle("alsa_output.platform-3f902000.hdmi.hdmi-stereo", 28) == "alsa_output.pl...hdmi-stereo"


def test_human_audio_sink_prefers_readable_name():
    item = human_audio_sink("alsa_output.platform-3f902000.hdmi.hdmi-stereo", default=True)
    assert item.primary == "TV HDMI"
    assert item.status == "[ACTIVE]"
    assert "alsa_output" in item.detail


def test_human_bt_device_uses_name_and_mac_detail():
    item = human_bt_device("Device 24:4B:03:92:0B:8C [Samsung] Soundbar J-Series", connected=True)
    assert item.primary == "[Samsung] Soundbar J-Series"
    assert item.status == "[CONNECTED]"
    assert item.detail == "24:4B:03:92:0B:8C"
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```bash
uv run pytest tests/test_tui_formatting.py -q
```

Expected: import failure because `rpi_dashboard.tui.formatting` does not exist.

- [ ] **Step 3: Implement formatting helpers**

Create `rpi_dashboard/tui/formatting.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DisplayItem:
    primary: str
    detail: str
    status: str = ""


def badge(value: str) -> str:
    clean = "".join(ch for ch in value.upper() if ch.isalnum() or ch in {"_", "-"})
    return f"[{clean}]"


def truncate_middle(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    if max_len < 8:
        return value[:max_len]
    left = (max_len - 3) // 2
    right = max_len - 3 - left
    return f"{value[:left]}...{value[-right:]}"


def human_audio_sink(sink_id: str, *, default: bool = False) -> DisplayItem:
    lowered = sink_id.lower()
    if "hdmi" in lowered:
        primary = "TV HDMI"
    elif "bluez" in lowered:
        primary = "Bluetooth Audio"
    elif "usb" in lowered:
        primary = "USB Audio"
    elif "dlna" in lowered or "lg_tv" in lowered or "windows_digital_media_renderer" in lowered:
        primary = "DLNA Renderer"
    else:
        primary = "Audio Output"
    return DisplayItem(primary=primary, detail=truncate_middle(sink_id, 44), status=badge("active") if default else "")


def human_bt_device(line: str, *, connected: bool = False, paired: bool = True) -> DisplayItem:
    parts = line.split(None, 2)
    mac = parts[1] if len(parts) >= 2 else "unknown"
    name = parts[2] if len(parts) >= 3 else "Unknown Bluetooth Device"
    state = "connected" if connected else ("paired" if paired else "found")
    return DisplayItem(primary=name, detail=mac, status=badge(state))
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
uv run pytest tests/test_tui_formatting.py -q
uv run ruff check rpi_dashboard/tui/formatting.py tests/test_tui_formatting.py
```

Expected: all pass.

Commit:

```bash
git add rpi_dashboard/tui/formatting.py tests/test_tui_formatting.py
git commit -m "feat(tui): add tv-safe display formatting"
```

## Task 2: Rename Live Tabs Into Task-Oriented Workflow

**Files:**
- Modify: `tui.py`
- Test: `tests/test_tui_modern.py`

- [ ] **Step 1: Add failing layout test for tab names and count**

Add this test to `tests/test_tui_modern.py`:

```python
def test_live_tui_uses_task_oriented_tabs():
    async def run_check():
        import tui
        from textual.widgets import TabbedContent, TabPane

        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause(0.2)
            tabs = app.query_one(TabbedContent)
            pane_ids = [pane.id for pane in app.query(TabPane)]
            assert pane_ids == [
                "tab_player",
                "tab_apps",
                "tab_audio",
                "tab_devices",
                "tab_network",
                "tab_system",
                "tab_logs",
            ]
            assert tabs.active == "tab_player"

    asyncio.run(run_check())
```

- [ ] **Step 2: Run the test and confirm failure**

Run:

```bash
uv run pytest tests/test_tui_modern.py::test_live_tui_uses_task_oriented_tabs -q
```

Expected: failure because current pane IDs are `tab_control` and `tab_settings`.

- [ ] **Step 3: Split composition into seven tabs without changing handlers**

In `tui.py`, update `compose()` so the first screen uses:

```python
with TabbedContent(initial="tab_player"):
    with TabPane("Player", id="tab_player"):
        ...
    with TabPane("Apps", id="tab_apps"):
        ...
    with TabPane("Audio", id="tab_audio"):
        ...
    with TabPane("Devices", id="tab_devices"):
        ...
    with TabPane("Network", id="tab_network"):
        ...
    with TabPane("System", id="tab_system"):
        ...
    with TabPane("Logs", id="tab_logs"):
        ...
```

Move existing widgets, do not rewrite behavior yet:

- Player: URL input, MPV button, playback-related status if present.
- Apps: SteamLink, GeForce Now, Spotify, Amazon Music, Stop.
- Audio: `list_audio_sinks`, volume buttons, latency input, Alexa switch, pa-dlna restart.
- Devices: `list_bluetooth_devices`, Bluetooth buttons.
- Network: `txt_network_info`, `txt_tailscale_info`, Wi-Fi list/input/buttons, hotspot and raspotify switches.
- System: safe restart placeholders only if buttons already exist; otherwise static service status.
- Logs: `Log(id="syslog")`.

Update `update_settings_data()` active-tab guard from:

```python
if active_tab != "tab_settings":
    return
```

to:

```python
if active_tab not in {"tab_audio", "tab_devices", "tab_network", "tab_system"}:
    return
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
uv run pytest tests/test_tui_modern.py -q
uv run ruff check tui.py tests/test_tui_modern.py
```

Expected: all pass.

Commit:

```bash
git add tui.py tests/test_tui_modern.py
git commit -m "feat(tui): split dashboard into task tabs"
```

## Task 3: Add Persistent ASCII Top Status Bar

**Files:**
- Modify: `tui.py`
- Test: `tests/test_tui_modern.py`

- [ ] **Step 1: Add failing test for top status bar**

Add:

```python
def test_live_tui_has_ascii_status_bar():
    async def run_check():
        import tui
        from textual.widgets import Static

        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(120, 35)) as pilot:
            await pilot.pause(0.5)
            status = app.query_one("#top_status", Static)
            rendered = str(status.render())
            assert "MODE:" in rendered
            assert "CPU:" in rendered
            assert "RAM:" in rendered
            assert all(ord(ch) < 128 for ch in rendered)

    asyncio.run(run_check())
```

- [ ] **Step 2: Run test and confirm failure**

Run:

```bash
uv run pytest tests/test_tui_modern.py::test_live_tui_has_ascii_status_bar -q
```

Expected: no `#top_status` widget.

- [ ] **Step 3: Implement `TopStatus` widget**

In `tui.py`, add:

```python
class TopStatus(Static):
    def on_mount(self) -> None:
        self._stats = SystemStats()
        self.set_interval(TUI_STATS_INTERVAL, self.update_status)
        self.update_status()

    def update_status(self) -> None:
        cpu = self._stats.get_cpu_usage()
        ram_used, ram_total = self._stats.get_ram_usage()
        temp = self._stats.get_cpu_temp()
        ip = self._stats.get_local_ip()
        self.update(
            f"MODE: IDLE | CPU: {cpu:.1f}% | RAM: {int(ram_used * 1024)}MB/{int(ram_total * 1024)}MB | "
            f"TEMP: {temp:.1f}C | IP: {ip} | API: {API_PORT}"
        )
```

Yield it once near the top of `compose()`:

```python
yield TopStatus(id="top_status")
```

Update CSS:

```css
#top_status {
    height: 1;
    padding: 0 1;
    background: $panel;
    color: $text;
}
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
uv run pytest tests/test_tui_modern.py -q
uv run ruff check tui.py tests/test_tui_modern.py
```

Expected: all pass.

Commit:

```bash
git add tui.py tests/test_tui_modern.py
git commit -m "feat(tui): add persistent status bar"
```

## Task 4: Rebuild Audio Tab With Human Labels

**Files:**
- Modify: `tui.py`
- Modify: `tests/test_tui_modern.py`
- Uses: `rpi_dashboard/tui/formatting.py`

- [ ] **Step 1: Add failing test for audio display**

Add:

```python
def test_audio_tab_uses_human_sink_labels(monkeypatch):
    async def run_check():
        import tui
        from textual.widgets import OptionList, TabbedContent

        async def fake_run_sys_cmd(self, cmd, timeout=5.0):
            if cmd == "pactl get-default-sink":
                return "alsa_output.platform-3f902000.hdmi.hdmi-stereo"
            if cmd == "pactl list short sinks":
                return "0\talsa_output.platform-3f902000.hdmi.hdmi-stereo\tPipeWire\n1\tbluez_sink.24_4B_03_92_0B_8C.a2dp_sink\tPipeWire"
            return ""

        monkeypatch.setattr(tui.RPiDashboard, "run_sys_cmd", fake_run_sys_cmd)
        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(120, 35)) as pilot:
            app.query_one(TabbedContent).active = "tab_audio"
            await app.update_audio_sinks()
            await pilot.pause(0.1)
            prompts = [
                str(app.query_one("#list_audio_sinks", OptionList).get_option_at_index(i).prompt)
                for i in range(app.query_one("#list_audio_sinks", OptionList).option_count)
            ]
            assert any("TV HDMI" in prompt and "[ACTIVE]" in prompt for prompt in prompts)
            assert any("Bluetooth Audio" in prompt for prompt in prompts)

    asyncio.run(run_check())
```

- [ ] **Step 2: Run test and confirm failure**

Run:

```bash
uv run pytest tests/test_tui_modern.py::test_audio_tab_uses_human_sink_labels -q
```

Expected: failure because prompts still expose long raw sink labels first.

- [ ] **Step 3: Update `update_audio_sinks()`**

Import:

```python
from rpi_dashboard.tui.formatting import human_audio_sink
```

Replace prompt building inside `update_audio_sinks()` with:

```python
item = human_audio_sink(sink_id, default=sink_id == default_sink)
label = f"{item.status} {item.primary} - {item.detail}".strip()
sinks_list.add_option(label)
```

Update `on_option_list_option_selected()` so it no longer parses sink IDs from the prompt. Store a mapping when refreshing:

```python
self._audio_sink_by_prompt = {}
...
self._audio_sink_by_prompt[label] = sink_id
```

Then select via:

```python
sink_id = getattr(self, "_audio_sink_by_prompt", {}).get(selected_text)
if sink_id:
    asyncio.create_task(self.set_audio_sink(sink_id))
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
uv run pytest tests/test_tui_formatting.py tests/test_tui_modern.py -q
uv run ruff check tui.py rpi_dashboard/tui/formatting.py tests/test_tui_modern.py tests/test_tui_formatting.py
```

Expected: all pass.

Commit:

```bash
git add tui.py tests/test_tui_modern.py
git commit -m "feat(tui): show human audio output labels"
```

## Task 5: Rebuild Devices Tab With Device Status Rows

**Files:**
- Modify: `tui.py`
- Modify: `tests/test_tui_modern.py`

- [ ] **Step 1: Add failing test for Bluetooth display**

Add:

```python
def test_devices_tab_shows_bluetooth_status_rows(monkeypatch):
    async def run_check():
        import tui
        from textual.widgets import OptionList, TabbedContent

        async def fake_run_sys_cmd(self, cmd, timeout=5.0):
            if cmd == "bluetoothctl devices Paired":
                return "Device 24:4B:03:92:0B:8C [Samsung] Soundbar J-Series\nDevice 5C:BA:37:01:74:E9 Xbox Wireless Controller"
            if cmd == "bluetoothctl devices Connected":
                return "Device 24:4B:03:92:0B:8C [Samsung] Soundbar J-Series"
            return ""

        monkeypatch.setattr(tui.RPiDashboard, "run_sys_cmd", fake_run_sys_cmd)
        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(120, 35)) as pilot:
            app.query_one(TabbedContent).active = "tab_devices"
            await app.update_bluetooth_devices()
            await pilot.pause(0.1)
            bt_list = app.query_one("#list_bluetooth_devices", OptionList)
            prompts = [str(bt_list.get_option_at_index(i).prompt) for i in range(bt_list.option_count)]
            assert any("[CONNECTED] [Samsung] Soundbar J-Series" in prompt for prompt in prompts)
            assert any("[PAIRED] Xbox Wireless Controller" in prompt for prompt in prompts)

    asyncio.run(run_check())
```

- [ ] **Step 2: Run test and confirm failure**

Run:

```bash
uv run pytest tests/test_tui_modern.py::test_devices_tab_shows_bluetooth_status_rows -q
```

Expected: failure because the current code does not merge connected state.

- [ ] **Step 3: Update `update_bluetooth_devices()`**

Use `human_bt_device()` and connected MAC detection:

```python
from rpi_dashboard.tui.formatting import human_bt_device

connected_out = await self.run_sys_cmd("bluetoothctl devices Connected")
connected_macs = {
    parts[1]
    for line in connected_out.splitlines()
    if line.startswith("Device ") and len(parts := line.split(None, 2)) >= 2
}
...
item = human_bt_device(line, connected=mac in connected_macs)
label = f"{item.status} {item.primary} - {item.detail}"
bt_list.add_option(label)
self._bt_mac_by_prompt[label] = item.detail
```

Update `run_bluetooth_action()` to prefer `_bt_mac_by_prompt` over parsing parentheses.

- [ ] **Step 4: Run tests and commit**

Run:

```bash
uv run pytest tests/test_tui_formatting.py tests/test_tui_modern.py -q
uv run ruff check tui.py rpi_dashboard/tui/formatting.py tests/test_tui_modern.py tests/test_tui_formatting.py
```

Expected: all pass.

Commit:

```bash
git add tui.py tests/test_tui_modern.py
git commit -m "feat(tui): show bluetooth device status rows"
```

## Task 6: Add Empty, Loading, And Error States

**Files:**
- Modify: `tui.py`
- Modify: `tests/test_tui_modern.py`

- [ ] **Step 1: Add failing tests for empty states**

Add:

```python
def test_wifi_empty_state_is_explanatory(monkeypatch):
    async def run_check():
        import tui
        from textual.widgets import OptionList

        async def fake_run_sys_cmd(self, cmd, timeout=5.0):
            return ""

        monkeypatch.setattr(tui.RPiDashboard, "run_sys_cmd", fake_run_sys_cmd)
        tui.API_PORT = 0
        app = tui.RPiDashboard()
        async with app.run_test(size=(120, 35)):
            await app.scan_wifi()
            wifi_list = app.query_one("#list_wifi_networks", OptionList)
            assert str(wifi_list.get_option_at_index(0).prompt) == "No Wi-Fi networks found. Run scan again or check adapter."

    asyncio.run(run_check())
```

- [ ] **Step 2: Run test and confirm failure**

Run:

```bash
uv run pytest tests/test_tui_modern.py::test_wifi_empty_state_is_explanatory -q
```

Expected: current prompt is `Žádné sítě`.

- [ ] **Step 3: Update user-facing empty labels**

In `scan_wifi()`, replace:

```python
wifi_list.add_option("Žádné sítě")
```

with:

```python
wifi_list.add_option("No Wi-Fi networks found. Run scan again or check adapter.")
```

Update `connect_wifi()` guard to compare this full string.

In `update_bluetooth_devices()`, when no devices exist, use:

```python
bt_list.add_option("No paired Bluetooth devices. Use Scan, then Pair.")
```

In audio fallback, use:

```python
sinks_list.add_option("[ERROR] No audio outputs reported by pactl")
```

- [ ] **Step 4: Run tests and commit**

Run:

```bash
uv run pytest tests/test_tui_modern.py -q
uv run ruff check tui.py tests/test_tui_modern.py
```

Expected: all pass.

Commit:

```bash
git add tui.py tests/test_tui_modern.py
git commit -m "feat(tui): add clear empty states"
```

## Task 7: TV Runtime Verification

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Run full local verification**

Run:

```bash
uv run ruff check .
uv run mypy .
uv run python -m pytest -q
```

Expected: ruff passes, mypy passes, pytest passes.

- [ ] **Step 2: Restart live TUI service**

Run:

```bash
sudo -n systemctl restart dashboard@milhy777.service
sleep 5
systemctl status dashboard@milhy777 --no-pager
```

Expected: service is active and running `/home/milhy777/rpi-dashboard/.venv/bin/python tui.py` on `tty1`.

- [ ] **Step 3: Inspect TV framebuffer**

Run:

```bash
sudo -n chvt 1
sudo -n sh -c 'setterm -blank poke < /dev/tty1 > /dev/tty1 2>/dev/null || true'
sudo -n cat /dev/vcs1 | tr '\000' ' ' | fold -w 120 | sed -n '1,45p'
```

Expected: top status bar is visible, tab names are ASCII-readable, Audio/Devices/Network pages no longer depend on emoji or raw sink IDs as primary labels.

- [ ] **Step 4: Manual interaction checklist on TV**

Verify manually:

- Switch every tab.
- Audio tab: select HDMI and confirm it remains mapped to the real sink.
- Devices tab: scan Bluetooth and confirm rows show human names and statuses.
- Network tab: run Wi-Fi scan and confirm empty state or SSID list is understandable.
- Apps tab: do not launch Chromium locally; Steam/GFN/mpv buttons may be tested only if user approves.
- System tab: do not reboot unless user explicitly approves.

- [ ] **Step 5: Update handoff docs and commit**

Append a short status note to `AGENTS.md` under `Current Refactor Handoff`:

```markdown
TUI operational dashboard iteration 1 has migrated the live `tui.py` path to task-oriented tabs with ASCII-safe labels, top status, and clearer Audio/Devices/Network states. Verify future TUI work against the live `dashboard@milhy777.service` on `tty1`; do not assume `rpi_dashboard/tui/modern.py` is production.
```

Commit:

```bash
git add AGENTS.md
git commit -m "docs(tui): update operational dashboard handoff"
```

## Task 8: Final Gate

**Files:**
- No code changes unless verification fails.

- [ ] **Step 1: Run repository completion checks**

Run:

```bash
tools/verify-done.sh
```

Expected: PASS. If it fails, capture the exact failing section and fix only the failing issue.

- [ ] **Step 2: Confirm git state**

Run:

```bash
git status --short
git log --oneline -8
```

Expected: no uncommitted tracked changes; recent commits show the TUI plan/fix sequence.

- [ ] **Step 3: Report outcome**

Final report should include:

- Commit hashes created.
- Verification commands and results.
- Whether TV runtime was visually inspected.
- Any intentionally skipped destructive actions.

