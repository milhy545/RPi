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
