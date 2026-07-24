# Bluetooth Control Center

The dashboard treats every Bluetooth relationship as `(adapter_id, device_key)`.
Two adapters remain independent, and a device bonded to one adapter is hidden as
an unpaired discovery shadow on the other adapter. A deliberate bond on both
adapters remains visible on both.

## Normal use

- Use the Bluetooth section in WebUI or the Bluetooth console in `tui.py`.
- Discovery is limited to 15 seconds in balanced mode or 30 seconds in
  aggressive mode, with a hard 60-second API limit.
- New pairing always requires an explicit Pair action. Confirmation, PIN, and
  passkey challenges are shown in WebUI/TUI and expire after 60 seconds.
- Automatic reconnect is enabled by default for paired and trusted devices.
  Each device has an opt-out. A manual disconnect suppresses reconnect for 60
  seconds; failures use capped exponential backoff and stable jitter.
- Profile actions are shown only for UUIDs advertised by the remote device.
  PipeWire card profiles, sink/source state, mute, codec, sample rate, and
  latency remain owned by the shared Audio service.

## PC interoperability

Capabilities are negotiated, not inferred from a device name. Windows and
Linux support depends on the roles actually exposed by both endpoints:

| Workflow | Required remote role | Local requirement | Status before hardware acceptance |
| --- | --- | --- | --- |
| RPi sends music | A2DP Sink | PipeWire A2DP Source | Conditional |
| RPi receives music | A2DP Source | PipeWire A2DP Sink | Conditional |
| Headset audio and microphone | Compatible HFP/HSP HF/AG pair | WirePlumber telephony backend | Conditional |
| Media controls and metadata | AVRCP Target/Controller | BlueZ MediaPlayer/MediaTransport | Implemented when advertised |
| File send/receive | OPP | `bluez-obexd` and dashboard agent | Code complete; package required |
| PAN or serial profile | PANU/NAP/GN or SPP | Remote service and BlueZ support | Exposed when advertised |
| Battery | Battery Service | BlueZ Battery1 | Read-only telemetry |
| Outbound keyboard/mouse HID | Remote HID host | Registered outbound HID profile and `/dev/uhid` | Unavailable on current host |

Windows may require its Bluetooth File Transfer window to be open for OPP and
does not expose every audio role on every version or adapter. Linux requires
BlueZ/PipeWire policy that enables the complementary role. The UI reports a
profile as unavailable instead of claiming that an unsupported direction works.

## File transfer

Outbound selection is limited to regular, non-symlink files in `~/Downloads`.
Inbound Object Push is accepted only from a device that BlueZ reports as paired
and trusted on the source adapter. The receive agent sanitizes the filename,
rejects traversal, checks the size limit and free space, writes to a private
`.part` file, and atomically finalizes a collision-safe name under
`~/Downloads`.

The default transfer limit is 512 MiB and the free-space reserve is 16 MiB.
`RPI_BLUETOOTH_MAX_TRANSFER_BYTES` can lower or raise the size limit.
`RPI_BLUETOOTH_DOWNLOAD_DIR` exists for isolated testing; production should
retain `~/Downloads`.

The host must have `bluez-obexd` installed. The provisioning dependency list
contains it, but the dashboard deliberately does not install packages or alter
the host during normal startup.

## Multi-output recovery

When two Bluetooth outputs are selected, the Audio service persists that
intent. If either output disappears, it first selects a real fallback sink and
then removes the stale `rpi_bt_multi_output` module. BlueZ device events trigger
a debounced reconciliation; when both requested outputs return, the combined
sink and Bluetooth input loopbacks are recreated. Status reads never mutate
PipeWire.

## Diagnostics and recovery

`GET /bt/diagnostics` reads bounded Bluetooth, kernel, and WirePlumber journals
and classifies known HCI timeout/frame/security, A2DP/HFP, Xbox HID/GATT/rumble,
and PipeWire xrun failures. It also reports component versions, adapter kernel
counters when available, process memory, load average, and CPU count.

Recovery order:

1. Stop discovery from WebUI/TUI and wait for the bounded scan to finish.
2. Check `/bt/state`, `/bt/diagnostics`, and `/audio/multi-output?action=status`.
3. Confirm the device appears only on its owning adapter unless it is genuinely
   bonded to both.
4. Use a deliberate Disconnect/Connect or profile action on that relationship.
5. Restart the dashboard only after preserving logs. A controller, BlueZ,
   PipeWire, kernel, firmware, or whole-RPi restart is a separate final action.

Current 2026-07-24 pre-restart evidence found BlueZ 5.66, PipeWire 1.2.7,
WirePlumber 0.4.13, repeated `hci0` command timeouts, and PipeWire xruns. The
running old UI started unbounded scans and retained a combine sink whose two
Bluetooth slaves were absent. The new bounded discovery and multi-output
reconciliation address those software causes; recurrence after restart is a
hardware acceptance failure, not a reason to silently reset both adapters.

## Security boundary

No unknown device is paired automatically. Incoming files require an existing
paired and trusted relationship. Outbound HID injection is disabled by default
and fails closed on this host because `/dev/uhid` and an outbound BlueZ HID
profile are absent. AVRCP remains the supported media-key path. Kernel module,
firmware, BlueZ experimental, boot, or audio-policy changes require separate
evidence, rollback instructions, and approval.
