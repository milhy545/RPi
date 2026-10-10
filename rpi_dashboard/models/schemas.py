"""Data models for RPi-TV Dashboard API responses."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ApiResponse:
    """Base API response."""
    ok: bool
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@dataclass
class AudioDevice:
    """Audio device information."""
    id: str
    name: str
    type: str  # hdmi, bt, dlna_output, usb_output, usb_input, remote_input
    present: bool
    volume: Optional[int] = None
    state: Optional[str] = None


@dataclass
class AudioState:
    """Complete audio state."""
    default_sink: Optional[str] = None
    default_source: Optional[str] = None
    sinks: List[AudioDevice] = field(default_factory=list)
    sources: List[AudioDevice] = field(default_factory=list)
    sink_inputs: List[Dict[str, Any]] = field(default_factory=list)
    devices: Dict[str, Any] = field(default_factory=dict)
    routes: Dict[str, Any] = field(default_factory=dict)
    bluetooth: Dict[str, Any] = field(default_factory=dict)
    latency: Dict[str, int] = field(default_factory=dict)
    cache: Optional[Dict[str, Any]] = None


@dataclass
class BluetoothDevice:
    """Bluetooth device information."""
    mac: str
    name: str
    type: str  # audio_output, gamepad, input, mobile, unknown
    paired: bool = False
    connected: bool = False


@dataclass
class WiFiNetwork:
    """WiFi network information."""
    ssid: str
    signal: int
    security: str = "none"
    active: bool = False


@dataclass
class WiFiStatus:
    """WiFi status."""
    available: bool
    connected: bool
    connected_ssid: Optional[str] = None
    networks: List[WiFiNetwork] = field(default_factory=list)


@dataclass
class MpvStatus:
    """MPV player status."""
    ok: bool
    on: bool = False
    pos: float = 0
    dur: float = 0
    paused: bool = False
    title: str = ""
    vol: int = 100
    q: str = "720p"
    idle: bool = False
    err: Optional[str] = None


@dataclass
class SystemStats:
    """System statistics."""
    cpu_percent: float = 0
    cpu_temp: float = 0
    ram: Dict[str, float] = field(default_factory=dict)
    disk: Dict[str, Any] = field(default_factory=dict)
    uptime: str = "unknown"


@dataclass
class CECDevice:
    """CEC device information."""
    address: str
    name: str
    manufacturer: str = ""
