# Audio Multi-Mixer and WebUI Refactor

## 1. Context and Problem Statement
The current audio stack and WebUI are inadequate and unstable. Audio only plays reliably through HDMI, and Bluetooth outputs (e.g., Samsung soundbar) drop connection after a few seconds. The UI lacks a cohesive way to manage the flow of audio from multiple sources (mpv, game streams, web sources) to multiple outputs (HDMI, Bluetooth, local). The user requires a complete refactor of the audio component into a true "multi-mixer" where any source can route to any sink, accompanied by a premium WebUI using Basic/Expert modes.

## 2. Desired Outcome
1. **Robust Audio Multi-Mixer (PipeWire/PulseAudio)**: 
   - Every audio source can play on every available audio sink simultaneously or individually.
   - Intelligent synchronization of BT & audio codecs and bitrates to prevent dropouts (specifically addressing the Samsung soundbar issue).
   - Intelligent audio delay/latency compensation to ensure seamless playback (no gaps/stuttering).
2. **Shiny New Audio WebUI Page**:
   - 100% E2E tested and fully working.
   - Built on the existing scaffold, utilizing the Audio Flow Topology Canvas.
   - **Basic Mode**: Horizontal navigation/layout, simple click-to-route functionality.
   - **Expert Mode**: Vertical side navigation, Drag & Drop (D&D) routing on the topology canvas.
   - The UI must look premium ("WOW" factor), utilizing modern styling, smooth animations, and clear visual representation of audio flows.
3. **TUI & Modularity**: Refactor the TUI to support these new audio capabilities, ensuring the backend is modular and extensible for future audio sources.
4. **Performance**: Must remain lightweight. Strict monitoring of system resources to prevent full RPi freezes.

## 3. Constraints and Assumptions
- Must use existing `/home/milhy777/rpi-dashboard` project structure.
- RPi resources are extremely limited (731MB RAM). No heavy polling in the JS frontend.
- PipeWire is the primary audio server.
- The `module-loopback` approach was recently merged for matrix links, which should be extended/optimized for the multi-mixer.
- All code changes must pass the strict CI checks (`verify-done.sh`).

## 4. Acceptance Criteria
- [ ] WebUI Audio tab features a fully styled Basic and Expert mode with interactive topology.
- [ ] Users can route any source to any sink via the WebUI (click in Basic, drag-and-drop in Expert).
- [ ] Bluetooth speakers (e.g., Samsung soundbar) maintain a stable connection indefinitely without dropping.
- [ ] Audio multi-mixer supports simultaneous routing without perceptible gaps or desync.
- [ ] Automated tests (Pytest + Playwright/Selenium for WebUI if applicable) pass 100%.
- [ ] TUI reflects basic audio routing capabilities.
- [ ] No regressions in RPi system stability or CPU/RAM starvation.
