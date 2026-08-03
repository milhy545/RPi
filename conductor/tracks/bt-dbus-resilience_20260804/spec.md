# Track Specification: BT D-Bus Resilience & Multi-Speaker Stability

## Overview
Řeší 4 klíčové kořenové příčiny nestability Bluetooth na RPi:

1. **D-Bus Crash Recovery**: Pády `blueZ D-Bus failed` způsobené synchronními blokujícími požadavky na `org.bluez` nebo ztrátou referencí na D-Bus proxy objekty při restartu BlueZ daemonu.
2. **BT Volume Desync (AVRCP ↔ PipeWire)**: Změna hlasitosti na BT reproduktoru se neprojeví v PipeWire a naopak.
3. **Multi-Speaker Dropouts**: Odpojování BT reproduktorů v multi-módu kvůli neslučitelným kodekům (A2DP SBC vs AAC) rozbíjí časování bufferu ve WirePlumberu/PulseAudio.
4. **Adapter Topology Blindness**: Uživatel neví, který adaptér (integrated Broadcom vs USB dongle) obsluhuje které zařízení a jaké jsou jeho limity.

## Acceptance Criteria
- Aplikace nesmí havarovat při manuálním zabití `bluetoothd` v systému (automatické zotavení).
- Přehrávání na HDMI + 1x BT a 2x BT musí běžet nepřerušeně déle než 1 hodinu.
- E2E testy procházejí s úspěšností 100 %.
- `tools/verify-done.sh` prochází s platným CI receipt.

## Transferred from audio-fullstack-refactor_20260725
- Bidirezionální BT volume sync (AVRCP ↔ PipeWire)
- AVRCP-focused unit tests
