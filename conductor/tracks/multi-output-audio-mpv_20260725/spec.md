# Specification: Multi-Output Audio Distribution for BT Source (Realme 8) & MPV Player

## Overview
Enable seamless, low-latency audio distribution from a Bluetooth input source (e.g. Realme 8 phone) and local media playback (MPV player / YouTube) simultaneously to multiple sinks: HDMI output, Bluetooth speakers (Samsung Soundbar, Tibo Sphere 2), and optional Wi-Fi/DLNA renderers.

## Motivation
Currently, `audio_multi_output()` in `rpi_dashboard/services/audio.py` only combines Bluetooth output sinks (`bluez_output.*`). It excludes physical HDMI audio (`alsa_output.platform-3f902000.hdmi.hdmi-stereo`). Furthermore, `mpv_start()` in `webserver.py` forcibly overrides the PipeWire default sink to HDMI on launch, which breaks active multi-output combine sinks. A Bluetooth source phone (Realme 8) requires clean A2DP Source profile routing into the PipeWire combine sink without buffer underruns or stutter on the RPi 3B+.

## Functional Requirements
- **FR-1**: Extend `audio_multi_output()` to include HDMI stereo (`alsa_output.platform-3f902000.hdmi.hdmi-stereo`) alongside Bluetooth sinks (`bluez_output.*`) inside the PipeWire combine sink (`rpi_bt_multi_output`).
- **FR-2**: Preserve PipeWire default sink state when launching `mpv` playback instead of hardcoding `set-default-sink HDMI`. If `rpi_bt_multi_output` is active, `mpv` streams to all combined outputs simultaneously.
- **FR-3**: Support A2DP input routing from mobile phones (e.g. Realme 8) using dynamic `module-loopback` into `rpi_bt_multi_output`.
- **FR-4**: Reconcile multi-output state gracefully when any output device (Bluetooth speaker or HDMI) connects or disconnects.
- **FR-5**: Provide anti-stutter latency tuning (PipeWire quantum 1024, sample rate 48000Hz, loopback latency 50ms) to prevent audio dropouts on RPi 3B+.

## Non-Functional Requirements
- **Performance**: Maintain low CPU overhead on RPi 3B+ (keep PipeWire/WirePlumber pinned to CPU Core 3, MPV to Cores 1-2).
- **Reliability**: Self-healing reconciliation on speaker disconnect/reconnect without losing persistent user intent.
- **Compatibility**: Retain full backward compatibility with existing single-sink switches (HDMI-only, Soundbar-only, DLNA-only).

## Acceptance Criteria
- [ ] Multi-output combine sink `rpi_bt_multi_output` includes both physical HDMI and connected Bluetooth output sinks.
- [ ] MPV playback streams through the active default sink (HDMI, BT, or Combine Sink) without resetting default sink to HDMI.
- [ ] Bluetooth input source (e.g., Realme 8 phone) routes cleanly through `rpi_bt_multi_output` to play on HDMI + BT speakers concurrently.
- [ ] `audio_multi_output("reconcile")` handles partial device disconnections without crashing or leaving dead default sinks.
- [ ] All automated unit tests in `tests/test_services_audio.py` and `tests/test_api_dispatch.py` pass.

## Constraints and Dependencies
- RPi 3B+ hardware constraint: 1GB RAM, shared 2.4GHz Wi-Fi/Bluetooth chip. Wired Ethernet is recommended when streaming 3 concurrent Bluetooth streams.
- PipeWire / WirePlumber user services running under UID 1000 (`milhy777`).

## Risks and Mitigations
- **Risk**: 2.4GHz interference between Wi-Fi and Bluetooth causing audio stutter.
  - *Mitigation*: Set PipeWire clock quantum to 1024, set loopback buffer latency to 50ms, pin RT audio threads to Core 3.
- **Risk**: Clock drift between HDMI hardware clock and Bluetooth device clocks.
  - *Mitigation*: PulseAudio `module-combine-sink` parameter `adjust_time=1` actively compensates for drift.

## Out of Scope
- Hardware modifications or external Bluetooth USB dongle setup (handled via standard RPi onboard bluetooth).
