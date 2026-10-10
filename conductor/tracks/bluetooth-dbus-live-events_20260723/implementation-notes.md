# Implementation Notes

## 2026-07-23 runtime recovery and live state

- The booted host was a lingering user with no active logind session. The
  installed WirePlumber 0.4 configuration therefore needs `with-logind=false`
  before `90-enable-all.lua`; the tracked `51-rpi-headless.lua` fragment keeps
  one standard WirePlumber instance and the installer disables the obsolete
  second Bluetooth-only instance.
- Both adapters are powered before the asynchronous startup autoconnect pass.
  Recovery does not run from a state-read request and cannot block WebUI/TUI.
- Speaker and phone audio endpoints use explicit remote A2DP Sink/Source
  `ConnectProfile` calls; other device classes retain generic `Device1.Connect`.
- BlueZ ObjectManager and Properties signals feed a bounded adapter-scoped
  event queue. A replacement D-Bus connection installs fresh match rules.
- Adapter/device arrival and property signals drive reconnect attempts outside
  HTTP requests. Failed attempts use capped exponential backoff with stable
  jitter, duplicate attempts are suppressed, and a successful manual
  disconnect creates a cooldown. Adapter-scoped per-device opt-out is exposed
  at `/bt/device-autoconnect`.
- When one adapter owns a device bond, an unpaired scan shadow with the same
  address on the other adapter is excluded. Two real bonds remain visible so
  an ambiguous existing configuration is never silently merged.

Live evidence before the final service restart:

- `hci0` and `hci1` both reported `Powered=true` after dashboard recovery.
- The realme phone reconnected through its owning `hci1` relationship.
- Direct A2DP profile negotiation created
  `bluez_output.24_4B_03_92_0B_8C.1` for the Samsung soundbar.
- Tibo Sphere 2 was rediscovered as paired, bonded, and trusted at
  `FC:58:FA:29:BA:47`; its final profile reconnect remains a controlled live
  check after the new code is loaded.

## 2026-07-24 profile, pairing, transfer, and failure work

- Device UUIDs now produce a negotiated capability model for audio directions,
  HFP/HSP, AVRCP, OPP, HID/HOGP, PAN, SPP, and battery telemetry. The Windows
  and Linux matrices deliberately remain conditional until remote OS tests.
- Pairing uses a BlueZ Agent1 bound to the exact selected device. Visible
  confirmation, authorization, PIN, and passkey challenges are asynchronous,
  bounded to 60 seconds, cancellable, and available in WebUI and `tui.py`.
  Legacy `/bt/pair` and `device-action?action=pair` use the same non-blocking
  lifecycle.
- Discovery started by the dashboard is now bounded per adapter (15 seconds in
  balanced mode, 30 in aggressive mode, hard maximum 60). The pre-restart UI
  previously started discovery on both adapters without an automatic stop,
  which is a plausible trigger for the repeated `hci0` command timeouts.
- The OBEX manager selects the source adapter, authorizes incoming OPP only for
  the paired/trusted owner, stages and atomically finalizes under `~/Downloads`,
  and exposes progress/cancellation. The host does not yet have `bluez-obexd`
  installed; provisioning now declares the package, and live transfer remains
  pending until package installation is separately approved and performed.
- AVRCP discovery, metadata, player operations, and transport volume are backed
  by BlueZ MediaPlayer1/MediaTransport1. Optional outbound HID is fail-closed:
  `/dev/uhid` and a registered outbound HID profile are absent, so the UI
  exposes the blocker and uses AVRCP as the safe media-key alternative.
- Bounded diagnostics classify every failure family listed in the spec and
  record BlueZ/PipeWire/WirePlumber versions and resource load. The current
  boot produced 65 `hci0` command-timeout matches and 28 PipeWire xrun matches
  in the bounded inputs; no other listed class was present in that snapshot.
- PipeWire already uses 48 kHz and quantum 1024, so no blind buffer change is
  applied. A stale `rpi_bt_multi_output` module referenced two absent Bluetooth
  sinks. The new debounced reconciliation switches to a physical fallback,
  removes the dangling module, preserves selected-output intent, and recreates
  the route when both outputs return.

Automated evidence before loading the new process: targeted Bluetooth, Audio,
API, asset, TUI, and domain tests passed (118 tests), with ruff and mypy clean.
The isolated Playwright run on Milhy-PC passed with 45 mocked adapter-aware
Bluetooth requests across desktop, tablet, and mobile viewport checks.
The first follow-up gateway attempt correctly failed because that temporary
WebUI server still owned test port 18090. PID 1422598 was identified and
terminated, the port was verified free, and the failed run was not treated as
evidence.
Hardware acceptance after restart remains required for both adapters, Samsung,
TIBO, Xbox, Windows/Linux roles, headset switching, and bidirectional OPP.
