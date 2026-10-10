# Track Specification: BT D-Bus Resilience & Multi-Speaker Stability

## Overview
Řeší 4 klíčové kořenové příčiny nestability Bluetooth na RPi:

1. **D-Bus Crash Recovery**: Pády `blueZ D-Bus failed` způsobené synchronními blokujícími požadavky na `org.bluez` nebo ztrátou referencí na D-Bus proxy objekty při restartu BlueZ daemonu.
2. **BT Volume Desync (AVRCP ↔ PipeWire)**: Změna hlasitosti na BT reproduktoru se neprojeví v PipeWire a naopak.
3. **Multi-Speaker Dropouts**: Odpojování BT reproduktorů v multi-módu kvůli neslučitelným kodekům (A2DP SBC vs AAC) rozbíjí časování bufferu ve WirePlumberu/PulseAudio.
4. **Adapter Topology Blindness**: Uživatel neví, který adaptér (integrated Broadcom vs USB dongle) obsluhuje které zařízení a jaké jsou jeho limity.
5. **Misleading WebUI Status**: The bottom status line currently contains hard-coded design claims (`Service Running`, `Bluetooth Ready`, and `Audio HDMI`) while hardware values update only after a separate hardware request. Every status badge, pill, summary, and quick-action state must derive from current backend evidence or explicitly show `unknown`, `stale`, `degraded`, `not applicable`, or an actionable error. Decorative green/ready/running states without backend provenance are forbidden across the WebUI.
6. **Incorrect BT Audio Readiness**: `PipeWire sink present` and `Audio route/loopback` remain blocked because readiness starts as `Owned by Audio service` and enrichment relies on the narrow `bt_soundbar` and `alexa_to_bt` model. Readiness must discover the actual connected Bluetooth audio sink and current PipeWire/WirePlumber route dynamically. An inactive optional loopback must not block otherwise valid BT playback, and absence of a connected BT audio device must be reported as `not applicable`, not as a false failure.

## Acceptance Criteria
- Aplikace nesmí havarovat při manuálním zabití `bluetoothd` v systému (automatické zotavení).
- Přehrávání na HDMI + 1x BT a 2x BT musí běžet nepřerušeně déle než 1 hodinu.
- The WebUI contains no hard-coded operational success state; each displayed status traces to a documented API field and refresh timestamp, with stale/error handling.
- With a connected and routable BT audio device, `PipeWire sink present` and the applicable audio-route readiness step become green from real PipeWire/WirePlumber evidence. With no BT audio device, they report `not applicable` without making global diagnostics falsely blocked.
- Backend tests cover sink/default-route/active-stream/optional-loopback/no-device/stale-command cases using command samples whose provenance is documented; Playwright tests prove loading, success, degraded, stale, and unavailable UI states.
- E2E testy procházejí s úspěšností 100 %.
- `tools/verify-done.sh` prochází s platným CI receipt.

## Transferred from audio-fullstack-refactor_20260725
- Bidirezionální BT volume sync (AVRCP ↔ PipeWire)
- AVRCP-focused unit tests
