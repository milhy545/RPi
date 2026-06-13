# Implementation Plan: Audio Routing and Mixer V2

## Phase 1: No-Install Audit
- [ ] Inspect current PipeWire sinks, sources, sink inputs, and source outputs.
- [ ] Identify current DLNA-related sinks/sources, if any.
- [ ] Verify TIBO/WiiMu/LG renderer discovery with existing `gssdp-discover` only.

## Phase 2: Backend Audio Model
- [ ] Add typed sink/source classification (`hdmi`, `bt`, `dlna_output`, `usb_output`, `usb_input`, `dlna_input`, `other`).
- [ ] Extend `/audio/state` with ordered outputs, inputs, mixer streams, and latency settings.
- [ ] Add `/audio/volume?kind=sink|source&name=...&volume=N` with clamping and validation.
- [ ] Add `/audio/default-sink?name=...` for generic safe output switching.
- [ ] Add local JSON persistence for DLNA latency/offset settings.

## Phase 3: Prototype UI
- [ ] Reorder outputs: HDMI first, then BT.
- [ ] Add inline volume sliders/buttons to every device card.
- [ ] Add mixer-style active stream section.
- [ ] Restore DLNA output switch button.
- [ ] Separate DLNA Input and DLNA Output cards.
- [ ] Add visible DLNA latency/offset control placeholder.

## Phase 4: E2E Validation
- [ ] Run Python syntax checks.
- [ ] Restart webserver only if mpv is not running.
- [ ] Verify `/audio/state` JSON.
- [ ] Verify volume endpoint rejects invalid device names.
- [ ] Verify UI still contains both stable `Audio` and `🧪 Test Audio` tabs.

## Phase 5: Future Renderer Research Gate
- [ ] Research `pa-dlna`/`pulseaudio-dlna`, `gmrender-resurrect`, `rygel`, GStreamer, and `mkchromecast` for Debian 12 aarch64 and 731 MiB RAM.
- [ ] Choose implementation only after research and user approval.
