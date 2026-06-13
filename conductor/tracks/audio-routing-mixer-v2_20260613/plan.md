# Implementation Plan: Audio Routing and Mixer V2

## Phase 1: No-Install Audit
- [x] Inspect current PipeWire sinks, sources, sink inputs, and source outputs.
- [x] Identify current DLNA-related sinks/sources, if any.
- [x] Verify TIBO/WiiMu/LG renderer discovery with existing `gssdp-discover` only.

## Phase 2: Backend Audio Model
- [x] Add typed sink/source classification (`hdmi`, `bt`, `dlna_output`, `usb_output`, `usb_input`, `dlna_input`, `other`).
- [x] Extend `/audio/state` with ordered outputs, inputs, mixer streams, and latency settings.
- [x] Add `/audio/volume?kind=sink|source&name=...&volume=N` with clamping and validation.
- [x] Add `/audio/default-sink?name=...` for generic safe output switching.
- [x] Add local JSON persistence for DLNA latency/offset settings.

## Phase 3: Prototype UI
- [x] Reorder outputs: HDMI first, then BT.
- [x] Add inline volume sliders/buttons to every device card.
- [x] Add mixer-style active stream section.
- [x] Restore DLNA output switch button.
- [x] Separate DLNA Input and DLNA Output cards.
- [x] Add visible DLNA latency/offset control placeholder.

## Phase 4: E2E Validation
- [x] Run Python syntax checks.
- [x] Restart webserver only if mpv is not running.
- [x] Verify `/audio/state` JSON with classified sinks/sources.
- [x] Verify `/audio/volume` rejects invalid device names.
- [x] Verify both `Audio` and `🧪 Test Audio` tabs present.
- [ ] Verify `/audio/state` JSON.
- [ ] Verify volume endpoint rejects invalid device names.
- [ ] Verify UI still contains both stable `Audio` and `🧪 Test Audio` tabs.

## Phase 5: Future Renderer Research Gate
- [ ] Research `pa-dlna`/`pulseaudio-dlna`, `gmrender-resurrect`, `rygel`, GStreamer, and `mkchromecast` for Debian 12 aarch64 and 731 MiB RAM.
- [ ] Choose implementation only after research and user approval.
