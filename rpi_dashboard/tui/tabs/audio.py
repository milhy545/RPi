"""TUI Audio tab with ASCII flow diagram and master volume control.

Provides a visual ASCII representation of audio routing (sources → sinks)
and a global master volume slider. All labels use diacritic-free Czech
for TV console (tty) compatibility.
"""

from __future__ import annotations

from typing import Any, Dict, List

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static

from rpi_dashboard.services.audio.state import audio_state


# ─── ASCII Flow Diagram ─────────────────────────────────────────────

class AudioFlowDiagram(Static):
    """Renders an ASCII diagram of active audio sources → sinks."""

    CSS = """
    #audio-flow-diagram {
        height: auto;
        min-height: 10;
        border: solid $accent;
        padding: 1;
        margin: 0 0 1 0;
        overflow-x: auto;
    }
    .flow-label {
        color: $text;
        text-style: bold;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._sources: List[Dict[str, Any]] = []
        self._sinks: List[Dict[str, Any]] = []
        self._default_sink: str = ""

    def update_flow(
        self,
        sources: List[Dict[str, Any]],
        sinks: List[Dict[str, Any]],
        default_sink: str = "",
    ) -> None:
        """Update the diagram data and re-render."""
        self._sources = sources
        self._sinks = sinks
        self._default_sink = default_sink
        self._render_ascii()

    def _render_ascii(self) -> None:
        """Build the ASCII flow diagram."""
        if not self._sources and not self._sinks:
            self.update("Zadne aktivni audio zdroje nebo vystupy.")
            return

        lines: List[str] = []
        lines.append("┌─────────────────────────────────────────────────────────┐")
        lines.append("│  Audio Flow: Zdroje → Mixer → Vystupy                  │")
        lines.append("├──────────────────────┬──────────────────────────────────┤")

        # Sources column (left)
        src_lines: List[str] = []
        for s in self._sources[:6]:
            name = s.get("name", "?")[:18]
            vol = s.get("volume")
            vol_str = f" {vol}%" if vol is not None else ""
            icon = _source_icon(s.get("type", ""))
            src_lines.append(f"│ {icon} {name:<16}{vol_str:>4} │")

        # Sinks column (right)
        snk_lines: List[str] = []
        for s in self._sinks[:6]:
            name = s.get("name", "?")[:18]
            vol = s.get("volume")
            vol_str = f" {vol}%" if vol is not None else ""
            is_def = " ★" if s.get("name") == self._default_sink else ""
            icon = _sink_icon(s.get("type", s.get("name", "")))
            snk_lines.append(f"│ {icon} {name:<16}{vol_str:>4}{is_def} │")

        # Merge side by side
        max_rows = max(len(src_lines), len(snk_lines), 1)
        for i in range(max_rows):
            left = src_lines[i] if i < len(src_lines) else "│" + " " * 22 + "│"
            right = snk_lines[i] if i < len(snk_lines) else "│" + " " * 34 + "│"
            lines.append(left[:-1] + "─┤" + right[1:])

        lines.append("├──────────────────────┴──────────────────────────────────┤")

        # Engine node in center
        lines.append("│              ╔═══════════════════╗                      │")
        lines.append("│              ║   🔊 PipeWire     ║                      │")
        lines.append("│              ╚═══════════════════╝                      │")
        lines.append("└─────────────────────────────────────────────────────────┘")

        self.update("\n".join(lines))


# ─── Sink List ───────────────────────────────────────────────────────

class AudioSinkList(Static):
    """Lists available audio sinks with status."""

    CSS = """
    #audio-sink-list {
        height: auto;
        min-height: 4;
        border: solid $secondary;
        padding: 1;
        margin: 0 0 1 0;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._sinks: List[Dict[str, Any]] = []
        self._default_sink: str = ""

    def update_sinks(
        self, sinks: List[Dict[str, Any]], default_sink: str = ""
    ) -> None:
        self._sinks = sinks
        self._default_sink = default_sink
        self._render_list()

    def _render_list(self) -> None:
        if not self._sinks:
            self.update("Zadne audio vystupy.")
            return

        lines = ["Vystupni zarizeni (sinks):", ""]
        for s in self._sinks:
            name = s.get("name", "?")
            vol = s.get("volume")
            vol_str = f" {vol}%" if vol is not None else ""
            is_def = " [VYCHOZI]" if name == self._default_sink else ""
            icon = _sink_icon(s.get("type", name))
            lines.append(f"  {icon} {name}{vol_str}{is_def}")

        self.update("\n".join(lines))


# ─── Master Volume Widget ────────────────────────────────────────────

class AudioMasterVolume(Static):
    """Global master volume display and label."""

    CSS = """
    #audio-master-volume {
        height: 3;
        border: solid $accent;
        padding: 0 1;
        margin: 0 0 1 0;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._volume: int = 100

    def update_volume(self, volume: int) -> None:
        self._volume = volume
        bar_len = 30
        filled = int(bar_len * volume / 100)
        bar = "█" * filled + "░" * (bar_len - filled)
        self.update(f" Hlasitost: [{bar}] {volume}%")


# ─── Main Audio Tab ──────────────────────────────────────────────────

class AudioTab(Vertical):
    """Complete Audio tab with flow diagram, sinks, and volume."""

    def compose(self) -> ComposeResult:
        yield AudioFlowDiagram(id="audio-flow-diagram")
        yield AudioSinkList(id="audio-sink-list")
        yield AudioMasterVolume(id="audio-master-volume")

    def refresh_audio(self) -> None:
        """Fetch audio state and update all sub-widgets."""
        try:
            state = audio_state(force=False)
        except Exception as e:
            self.notify(f"Chyba nacteni audio: {e}", severity="error")
            return

        if not state or state.get("error"):
            return

        # Extract sources and sinks
        sources = state.get("sources", [])
        sinks_list: List[Dict[str, Any]] = []

        # Build sink list from devices
        devices = state.get("devices", {})
        for dev_key in ("hdmi", "bt_soundbar", "dlna_output", "usb_output"):
            dev = devices.get(dev_key)
            if dev and dev.get("present"):
                sinks_list.append({
                    "name": dev.get("name", dev_key),
                    "type": dev_key,
                    "volume": dev.get("volume"),
                    "present": dev.get("present", False),
                })

        default_sink = state.get("default_sink", "")

        # Update widgets
        flow = self.query_one("#audio-flow-diagram", AudioFlowDiagram)
        flow.update_flow(sources, sinks_list, default_sink)

        sink_list = self.query_one("#audio-sink-list", AudioSinkList)
        sink_list.update_sinks(sinks_list, default_sink)

        # Compute average volume for master display
        vols = [
            d.get("volume")
            for d in sinks_list
            if d.get("volume") is not None
        ]
        avg_vol = int(sum(vols) / len(vols)) if vols else 100
        master = self.query_one("#audio-master-volume", AudioMasterVolume)
        master.update_volume(avg_vol)


# ─── Helpers ─────────────────────────────────────────────────────────

def _source_icon(source_type: str) -> str:
    """Return an icon for a given audio source type."""
    icons = {
        "usb_input": "🎙",
        "remote_input": "🎮",
        "dlna_input": "📡",
        "system": "🎵",
    }
    return icons.get(source_type, "🔊")


def _sink_icon(sink_type: str) -> str:
    """Return an icon for a given audio sink type."""
    lower = sink_type.lower()
    if "hdmi" in lower:
        return "📺"
    if "bluez" in lower or "bt" in lower:
        return "🔈"
    if "dlna" in lower or "wiimu" in lower or "linkplayer" in lower:
        return "📡"
    if "usb" in lower:
        return "🔌"
    return "🔊"
