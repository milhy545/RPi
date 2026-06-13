# Specification: Audio Routing and Mixer V2

## Goal
Refine the WebUI audio prototype into a durable audio routing and mixer panel that handles HDMI, Bluetooth, DLNA input, and DLNA output correctly on the live Raspberry Pi.

## User Feedback Incorporated
1. DLNA must be modeled as both:
   - **Input:** audio arriving from another PC/device on the network via `pa-dlna`/UPnP sender.
   - **Output:** RPi sends all or selected audio to a DLNA speaker/renderer such as TIBO Sphere 2.
2. HDMI output must be listed first, above Bluetooth.
3. Every device with a volume indicator must allow volume adjustment.
4. The UI needs a mixer-like view similar to Windows/Linux sound mixers.
5. Restore a DLNA button for switching RPi audio output to DLNA.
6. DLNA output latency must be visible and eventually compensatable.

## Requirements
- Keep changes in `🧪 Test Audio` until the user approves replacing the stable `Audio` tab.
- Display output sinks in this order:
  1. HDMI
  2. Bluetooth Soundbar
  3. DLNA output renderers/sinks
  4. USB analog output, if present
- Display input sources separately:
  1. USB Alexa input
  2. DLNA/network input, if available
  3. Other PipeWire sources
- Provide per-device volume controls for every sink/source that exposes volume via `pactl`.
- Add backend endpoints for setting sink/source volume safely.
- Add a mixer section listing active sink inputs/source outputs where feasible.
- Restore a visible DLNA output switch button in the prototype tab.
- Show DLNA latency/offset controls as a first-class concept even if full compensation requires a later renderer implementation.
- Do not install `pa-dlna`, `gmrender`, `rygel`, or any renderer without separate compatibility research and user approval.

## DLNA Architecture Notes
- **DLNA input** means another network device streams audio into the RPi. This likely requires a UPnP/DLNA renderer on the RPi or a bridge service that exposes a sink/source into PipeWire.
- **DLNA output** means the RPi sends audio to an external renderer. This may be implemented with `pulseaudio-dlna`/`pa-dlna`, `mkchromecast`, GStreamer, or a custom UPnP AVTransport sender, subject to research.
- DLNA output latency can be large and device-dependent. UI must expose configured offset and measured/estimated latency separately.

## Acceptance Criteria
- [ ] HDMI appears above Bluetooth in `🧪 Test Audio` output sinks.
- [ ] Volume can be adjusted from WebUI for HDMI, BT, and USB devices when present.
- [ ] `/audio/state` exposes sink/source volume and type metadata.
- [ ] `/audio/volume` safely sets sink/source volume with clamped values.
- [ ] `🧪 Test Audio` contains a mixer-style section for active audio streams.
- [ ] DLNA output switch button is visible again.
- [ ] DLNA input/output are represented separately in the UI.
- [ ] DLNA latency/offset field is represented in the UI and persisted locally.
- [ ] No stable `Audio` tab replacement happens without explicit approval.
