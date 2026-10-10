# Specification: Complete Bluetooth Hub and PC Interoperability

## Overview

Turn the two-adapter Bluetooth control center into a complete, profile-aware
Bluetooth hub. It must support Windows and Linux PCs, audio input and output,
headsets and microphones, media and optional HID control, file transfer, safe
pairing, live D-Bus events, and automatic reconnection of paired devices.

The dashboard must expose only capabilities that the local adapter, BlueZ,
PipeWire/WirePlumber, and remote device actually negotiate. Unsupported remote
OS/profile combinations must be reported explicitly instead of presented as
working.

## Motivation and Current Evidence

The current backend rebuilds state through `GetManagedObjects`, but its event
stream is empty, cancellation is unsupported, and conflicting operations are
not serialized. `obexctl` is installed, but there is no managed receive agent
that guarantees delivery to `~/Downloads`.

The 2026-07-23 boot logs also show Bluetooth and audio failures that this track
must diagnose and disposition:

- `hci0` command timeouts and frame reassembly failures during discovery;
- `hci1: security requested but not available`;
- A2DP source busy and HFP/HSP connection-refused failures with a PC/phone;
- Xbox HID/GATT report and battery notification errors plus a 16-second rumble
  initialization;
- Bluetooth/HDMI/USB PipeWire xruns and profile transitions.

The host currently advertises Audio Sink, Audio Source, AVRCP, HFP/HSP roles,
and has BlueZ 5.66, PipeWire 1.2.7, and WirePlumber 0.4.13. Profile behavior
must be verified against these installed versions before any upgrade or system
configuration change.

## Functional Requirements

### Live state and operation lifecycle

- Subscribe to BlueZ `InterfacesAdded`, `InterfacesRemoved`, and
  `PropertiesChanged` signals and recover subscriptions after reconnect.
- Serialize conflicting operations per stable adapter/device identity.
- Expose progress, status, cancellation, timeouts, and structured errors.
- Preserve independent control of both adapters and adapter-scoped device keys.

### Pairing and automatic reconnection

- Provide explicit pair, confirm/passkey, trust/untrust, connect by profile,
  disconnect, block/unblock, remove, and cancel-pairing operations.
- Automatically attempt reconnection for every paired device when it returns
  to range, using its owning adapter and supported profiles.
- Use bounded exponential backoff, jitter, duplicate-attempt suppression, and
  a per-device opt-out. A manual disconnect must suppress immediate reconnect
  for a documented cooldown.
- Resolve competing audio-profile or adapter claims deterministically without
  preventing unrelated devices from reconnecting.
- Never perform unattended first-time pairing or silently accept an unknown
  device.

### Windows and Linux PC capability matrix

- Detect and display negotiated support for A2DP source/sink, HFP/HSP HF/AG,
  AVRCP/media player control, HID/HOGP, OPP/OBEX, PAN/BNEP, SPP/RFCOMM,
  battery/GATT, and other BlueZ-exposed services.
- Test supported workflows with a Windows 10/11 PC and a BlueZ/PipeWire Linux
  PC. Record OS-side prerequisites and known one-way/unsupported combinations.
- Provide a profile selector, connection state, role direction, codec, sample
  rate, latency, and actionable failure reason in WebUI and live TUI.

### Audio, headset, and control

- Support RPi audio sent to a compatible PC, speaker, headset, or soundbar
  through A2DP Source.
- Support audio received from a compatible Windows/Linux PC or phone through
  A2DP Sink and route it through the existing PipeWire audio service.
- Support bidirectional headset/voice operation through compatible HFP/HSP
  roles, including microphone capture, output, mute, volume, and observable
  A2DP-to-HFP profile switching.
- Support AVRCP play, pause, stop, next, previous, volume, metadata, and player
  status where the remote player exposes them.
- Support explicitly enabled HID keyboard/mouse/media-key control of a paired
  PC where the remote OS accepts the profile. HID injection must be disabled by
  default and limited to trusted devices and deliberate user actions.
- Keep all final sink/source selection and loopback ownership in the shared
  Audio service; Bluetooth supplies profiles and transports rather than a
  second independent routing implementation.

### Bluetooth file transfer

- Send files to compatible Windows/Linux devices through OBEX Object Push.
- Run an authorization agent for incoming Object Push transfers and store
  accepted files under `/home/milhy777/Downloads` (`~/Downloads`).
- Accept automatically only from explicitly trusted/allowed devices; otherwise
  require a visible confirmation.
- Sanitize filenames, prevent path traversal and unsafe overwrite, use atomic
  finalization, check free space and configurable size limits, and preserve the
  original filename with collision-safe renaming.
- Expose transfer source/destination, progress, speed, status, cancellation,
  completion path, and structured failure reasons in API, WebUI, and TUI.

### Diagnostics and optimization

- Add a bounded diagnostic view for adapter firmware/transport, RSSI, profile
  negotiation, reconnect history, D-Bus errors, xruns, and transfer failures.
- Reproduce or safely simulate every Bluetooth-related log class listed above,
  identify its layer, and add a fix, mitigation, or explicit non-actionable
  disposition with verification evidence.
- Measure CPU, memory, wakeups, reconnect traffic, audio xruns, and per-core
  load before and after changes; prioritize core 0 and the 731 MiB RAM limit.

## Non-Functional Requirements

- Performance: no unbounded polling, event history, reconnect loop, or file
  queue; idle overhead must remain negligible on the Raspberry Pi 3B.
- Reliability: two adapters and unrelated paired devices remain independently
  usable through BlueZ, PipeWire, or dashboard restarts.
- Security and privacy: no automatic first pairing, unrestricted HID injection,
  arbitrary receive path, traversal, or silent file overwrite.
- Compatibility: feature claims are based on negotiated profiles and tested OS
  behavior, not device names or assumptions.

## Acceptance Criteria

- [ ] Fake-bus tests prove add/remove/property events and reconnect recovery.
- [ ] Every paired test device reconnects on return to range with bounded
  backoff; manual disconnect and per-device opt-out work.
- [ ] Windows and Linux capability matrices show tested audio, headset, control,
  file-transfer, HID, PAN, SPP, battery, and unsupported-profile outcomes.
- [ ] Compatible A2DP input/output and HFP/HSP headset paths produce usable
  PipeWire nodes with tested routing, volume, mute, latency, and profile switch.
- [ ] Compatible AVRCP and explicitly enabled HID controls work without stealing
  or duplicating input intended for the dashboard.
- [ ] OBEX send and receive work in both directions with accepted files finalized
  safely under `~/Downloads` and visible progress/cancellation.
- [ ] Pairing, profile connect/disconnect, operation status, and cancellation
  have tested adapter-aware API routes and matching WebUI/TUI controls.
- [ ] Each Bluetooth-related log failure has a verified fix, mitigation, or
  evidence-backed disposition; regression checks cover fixed classes.
- [ ] Live verification shows both adapters, the existing soundbar, Xbox
  controller, and at least one Windows and one Linux PC without cross-adapter
  interference.
- [ ] Legacy Bluetooth routes remain deterministic during their documented
  migration window.

## Constraints and Dependencies

- BlueZ D-Bus Device, Media, Profile, Input, Network, and OBEX APIs.
- PipeWire/WirePlumber profile policy; installed WirePlumber 0.4 syntax must be
  respected unless a separately researched and approved upgrade occurs.
- Windows and Linux expose different local Bluetooth roles; a remote OS cannot
  be forced to offer a profile it does not implement.
- Browser-heavy verification runs remotely from Milhy-PC.
- System package, BlueZ experimental, kernel, firmware, or boot changes require
  compatibility research, rollback instructions, and explicit approval.

## Risks

- Audio roles can conflict or reduce quality when a microphone activates HFP;
  show the profile switch and restore A2DP when capture ends.
- Automatic reconnect can thrash or seize the wrong audio route; use per-device
  policy, cooldown, profile priority, and bounded retries.
- An OBEX receiver expands the attack surface; restrict devices, paths, sizes,
  filenames, and authorization.
- HID control can inject unintended input; keep it opt-in with an immediate
  disable path and audit log.
- Old adapters or remote OSes may not implement all profiles; report the exact
  negotiated limitation and retain unaffected features.

## Out of Scope

- Claiming or emulating a profile that neither endpoint supports.
- Unattended pairing of unknown devices or accepting files/HID control from
  untrusted devices.
- Replacing the complete PipeWire Audio subsystem; Bluetooth-specific profile
  and route integration is in scope.
- Automatic kernel, firmware, BlueZ experimental, or boot configuration changes
  without a separate evidence and approval gate.

## Primary References

- BlueZ Device API: https://bluez.readthedocs.io/en/latest/device-api/
- BlueZ Media API: https://bluez.readthedocs.io/en/latest/media-api/
- BlueZ OBEX API: https://bluez.readthedocs.io/en/latest/obex-api/
- BlueZ OBEX Agent API: https://bluez.readthedocs.io/en/latest/obex-agent-api/
- WirePlumber Bluetooth configuration:
  https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/bluetooth.html
- Windows Bluetooth profiles:
  https://learn.microsoft.com/en-us/windows-hardware/drivers/bluetooth/general-bluetooth-support-in-windows
