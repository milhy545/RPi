## Background
The user wants a companion Android app similar to Kore (Kodi Remote) to share URLs/videos to the RPi for playback, control playback, and control the TV via CEC. The RPi cannot act as a Chromecast target, so sharing URLs to an API is the required solution. The RPi currently exposes APIs for `mpv` playback and CEC control on port 8090.
This plan is split into two tracks: Track A implements a PWA Web Share Target in the existing RPi dashboard as a quick fallback. Track B designs a separate Native Android Companion App in a new repository.

## Phase 1: Track A - PWA Web Share Target Implementation (RPi Repo)
- [ ] Task: Create `dashboard/static/manifest.json` with a Web Share Target configuration.
  - File: `dashboard/static/manifest.json`
  - Action: Define `name`, `short_name`, `start_url`, `display`, and `share_target` (handling `GET` with `title`, `text`, `url` params pointing to a share handler route).
- [ ] Task: Create a service worker `dashboard/static/sw.js` to handle installation, offline caching, and intercepting share target requests.
  - File: `dashboard/static/sw.js`
  - Action: Add `install` and `fetch` event listeners. Handle the share URL by extracting the shared `url` and posting it to the existing `/mpv/play` endpoint.
- [ ] Task: Update the main dashboard HTML to link the manifest and register the service worker.
  - File: `dashboard/templates/index.html`
  - Action: Add `<link rel="manifest" href="/static/manifest.json">` and a `<script>` block to register `/static/sw.js`.
- [ ] Verify: `curl -s http://localhost:8090/static/manifest.json | grep share_target`

## Phase 2: Track B - Native Android Companion App Design (Separate Repo) & RPi API Enhancements
- [ ] Task: [ANDROID-REPO] Initialize a new Android project for the companion app.
  - File: `app/build.gradle.kts`
  - Action: Set up Android project with dependencies: Retrofit (network), Coroutines, and NSD (for mDNS).
- [ ] Task: [ANDROID-REPO] Implement mDNS discovery to automatically find the RPi on the local network (`rpi-tv.local`).
  - File: `app/src/main/java/com/rpi/companion/DiscoveryService.kt`
  - Action: Use Android's `NsdManager` to discover `_http._tcp` services, with manual Tailscale IP entry as fallback.
- [ ] Task: [ANDROID-REPO] Create a Share Intent Receiver to catch "Share" actions from YouTube, Chrome, etc.
  - File: `app/src/main/AndroidManifest.xml`
  - Action: Add `<intent-filter>` for `android.intent.action.SEND` with `text/plain`. Extract URL and send POST to `http://<RPi-IP>:8090/mpv/play?url=<URL>`.
- [ ] Task: [ANDROID-REPO] Build the Remote Control UI with playback and CEC controls.
  - File: `app/src/main/java/com/rpi/companion/RemoteFragment.kt`
  - Action: Map UI buttons to RPi endpoints: `/mpv/stop`, `/mpv/toggle`, `/cec/nav`, `/cec/power`, `/cec/input`, `/audio/volume`.
- [ ] Task: [ANDROID-REPO] Implement a built-in WebView browser with video URL detection for sites without share buttons.
  - File: `app/src/main/java/com/rpi/companion/BrowserFragment.kt`
  - Action: Intercept web requests to find media URLs or inject JS to extract video elements, then send to RPi `/mpv/play`.
- [ ] Task: Add an explicit Now Playing / Status enhancement if missing in RPi backend.
  - File: `dashboard/api.py`
  - Action: Ensure `/mpv/status` returns detailed JSON with current media title, position, duration, and playback state for the Android App's "Now Playing" display.
- [ ] Verify: `curl -s http://localhost:8090/mpv/status | grep state`

## Acceptance Criteria
- [ ] PWA Web Share Target is registered and functional on mobile browsers.
- [ ] `manifest.json` and `sw.js` are served correctly by the RPi backend.
- [ ] Native Android App architecture is clearly defined for the separate repository.
- [ ] All existing tests pass: `uv run python -m pytest -q`
- [ ] Lint passes: `uv run ruff check .`
- [ ] `tools/verify-done.sh` passes
