# Plan: Finish and tune Devices tab

## Phase 1 — Discovery
- [x] Audit current devices APIs and UI gaps

## Phase 2 — Design
- [x] Improve Bluetooth/Wi-Fi/device role flows

## Phase 3 — Implementation
- [x] Enhanced `devices_state()` with Wi-Fi details, USB health, battery level
- [x] Added `_wifi_connection_details()` — SSID, signal, IP, frequency
- [x] Added `_usb_device_health()` — USB devices + storage info
- [x] Added `_bt_battery_level()` — read BT battery via upower
- [x] Improved `_bt_kind()` — classification for speakers, controllers, input, TV
- [x] Devices tab HTML: Wi-Fi status section, USB & Storage section
- [x] JS: `devicesRefresh()` renders Wi-Fi status and USB health
- [x] JS: `renderBtDevices()` shows battery, kind badge, remediation hints
- [x] JS: `deviceBtScan()` shows loading state
- [x] JS: `wifiConnect()` shows error remediation messages
- [x] JS: `wifiStatus()` renders formatted device list instead of raw JSON

## Phase 4 — Validation
- [x] `py_compile` passes for webserver_8099.py and tui.py
- [x] All new functions tested: _bt_kind, _wifi_connection_details, _usb_device_health, _bt_battery_level
- [x] Selftest (selftest_testaudio) passes with ok: True
- [x] No regression to existing playback, audio, devices, and terminal flows
