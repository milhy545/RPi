# Implementation Plan: Complete Bluetooth Hub and PC Interoperability

## Phase 1: Capability and failure baseline

- [ ] Task: Record both adapters, all paired devices, local/remote UUIDs,
  BlueZ/PipeWire/WirePlumber versions, profile roles, OBEX state, and resources.
- [ ] Task: Build a Windows/Linux capability matrix from official profile APIs
  and verified remote OS behavior; document unsupported direction combinations.
- [ ] Task: Turn each Bluetooth/audio/HID log class from the 2026-07-23 audit
  into a reproducible check, safe simulation, or explicit diagnostic procedure.

## Phase 2: Live events and operation lifecycle

- [x] Task: Add fake D-Bus signal/reconnect tests and subscribe to ObjectManager
  plus Properties signals with bounded event history.
- [x] Task: Reconcile and resubscribe after BlueZ/D-Bus reconnect without
  merging adapter state.
- [ ] Task: Add adapter/device-scoped conflict serialization, operation lookup,
  cancellation, structured errors, and tested API routes.

## Phase 3: Pairing and automatic reconnection

- [x] Task: Recover adapter-scoped pairing after reboot, keep pairability
  bounded to explicit user operations, and prevent Bluetooth timeouts from
  stalling the live WebUI/TUI service.
- [x] Task: Restore powered state for all present adapters before startup
  autoconnect and keep the recovery pass off the WebUI/TUI request path.
- [x] Task: Hide an unpaired discovery shadow on the non-owning adapter when
  exactly one adapter owns the device bond; preserve explicit dual bonds.
- [ ] Task: Add tested pairing-agent flows for confirmation, passkey, trust,
  block, removal, profile connect/disconnect, and cancellation.
- [x] Task: Implement automatic reconnect for all paired devices with owning
  adapter, profile priority, bounded backoff/jitter, cooldown, and deduplication.
- [ ] Task: Add per-device autoconnect opt-out and tests for manual disconnect,
  device absence, adapter restart, competing audio profiles, and two adapters.

## Phase 4: Windows/Linux audio and headset roles

- [ ] Task: Characterize A2DP Source/Sink and HFP/HSP HF/AG behavior on the
  installed WirePlumber 0.4 stack before selecting configuration changes.
- [ ] Task: Add profile selection and PipeWire integration for compatible audio
  input, output, headset microphone, volume, mute, codec, latency, and routing.
- [ ] Task: Test A2DP/HFP switching, recovery, and quality with Windows, Linux,
  the Samsung soundbar, and a compatible headset/phone.
- [ ] Task: Diagnose and mitigate profile-busy, connection-refused, xrun,
  buffer, `hci0`, and `hci1` security failures without harming the other adapter.

## Phase 5: Media, HID, and advanced profiles

- [ ] Task: Add AVRCP player discovery, metadata, playback, track, and volume
  controls with capability-specific errors.
- [ ] Task: Design an opt-in trusted-device HID control boundary, then add
  keyboard/mouse/media-key operations and an immediate disable path.
- [ ] Task: Expose discovered PAN/BNEP, SPP/RFCOMM, battery/GATT, and other
  supported profiles; implement safe connect/control actions where available.

## Phase 6: OBEX file transfer

- [ ] Task: Add fake OBEX agent/client tests for authorization, traversal,
  collisions, limits, low disk, failure, cancellation, and atomic completion.
- [ ] Task: Implement trusted-device receive authorization into `~/Downloads`
  and outbound OPP sessions using adapter/source selection.
- [ ] Task: Add API, WebUI, and live TUI send/receive progress, destination,
  cancellation, completion path, and error presentation.
- [ ] Task: Verify bidirectional transfers with Windows and Linux PCs using
  harmless test files and confirm no write can escape `~/Downloads`.

## Phase 7: Unified UI, diagnostics, and optimization

- [ ] Task: Add a profile/capability matrix, autoconnect policy, audio/headset,
  media/HID, file transfer, and failure diagnostics to WebUI and live `tui.py`.
- [ ] Task: Measure idle/active CPU, RAM, wakeups, reconnect traffic, xruns,
  transfer throughput, and per-core load; tune only against recorded evidence.
- [ ] Task: Run focused domain, BlueZ, OBEX, Audio, API, WebUI, TUI, security,
  and remote Windows/Linux interoperability checks.
- [ ] Task: Update user, recovery, adapter replacement, profile limitation,
  autoconnect, file-transfer, and security documentation.

## Completion

- [ ] Acceptance criteria verified, including controlled hardware checks.
- [ ] `tools/verify-done.sh` passed with a valid receipt.
