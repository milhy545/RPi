# Migration Map — backend-modularization-completion_20260723

## Target ownership model

- **`webserver.py`** stays as the supported production HTTP/HTTPS/WebSocket host, but only as a thin runtime shell.
- **`rpi_dashboard/api/routes.py` + `rpi_dashboard/api/handlers.py`** are the canonical API dispatch layer.
- **`rpi_dashboard/services/*`** are the service owners for business logic.
- **`tui.py`** remains the production TUI; `tui.py --headless` stays a test-only compatibility runner until replaced by the shared API registry.
- **`rpi_dashboard/tui/modern.py`** remains prototype-only.

## Migration order

1. Package entrypoint and startup surface.
2. Audio and MPV legacy compatibility endpoints.
3. Terminal ownership and headless route duplication.
4. Bluetooth / devices / DLNA legacy shims.
5. CEC legacy shims.
6. System / maintenance legacy shims.
7. YouTube / preview legacy shims.
8. Only then consider route removal, in small revertible batches.

## Route groups

| Legacy route(s) | Current consumer(s) | Target owner / replacement | Migration state | Deprecation signal | Rollback path |
|---|---|---|---|---|---|
| `/audio/bt`, `/audio/hdmi`, `/audio/dlna`, `/audio/mute` | WebUI audio controls, operator habits, legacy scripts | `rpi_dashboard/services/audio.py` via `audio_state`, `audio_set_default`, `audio_set_mute`, `audio_multi_output` | Compatibility only | `legacy_webserver_endpoint` JSON marker, logged hit | Restore legacy branches in `webserver.py` and route table entries |
| `/audio/route/alexa-bt`, `/audio/route/alexa-retarget` | WebUI Route cards / audio outputs | `rpi_dashboard/services/audio.py` Alexa routing helpers | Compatibility only | Legacy JSON marker + route hit logging | Restore the inline helper branches in `webserver.py` |
| `/audio/route/dlna-input/mode`, `/audio/route/dlna-input/start`, `/audio/route/dlna-input/status`, `/audio/route/dlna-input/stop`, `/audio/route/dlna-input/target` | WebUI Route cards, manual audio routing operations | `rpi_dashboard/services/audio.py` DLNA input helpers | Compatibility only | Legacy JSON marker + route hit logging | Restore the inline DLNA input branches |
| `/mpv/toggle`, `/mpv/seekabs`, `/mpv/vol`, `/mpv/memory`, `/mpv/memory/clear`, `/mpv/memory-save` | Player tab, playback memory workflows, saved URLs | `rpi_dashboard/services/player.py` + `rpi_dashboard/services/audio.py` for memory/cache helpers | Compatibility only | Legacy JSON marker + route hit logging | Restore legacy MPV branches in `webserver.py` |
| `/devices`, `/devices/bt/scan`, `/dlna/*` | Devices tab, Bluetooth/DLNA helpers, mobile/browser consumers | `rpi_dashboard/services/devices.py` + `rpi_dashboard/services/bluetooth/*` | Compatibility only | Legacy JSON marker + route hit logging | Restore the inline device/DLNA branches |
| `/cec/send`, `/cec/key`, `/cec/in`, `/cec/br/start`, `/cec/br/stop`, `/cec/br/st` | CEC remote actions and bridge maintenance | `rpi_dashboard/services/cec.py` | Compatibility only | Legacy JSON marker + route hit logging | Restore the inline CEC branches |
| `/system/hw-stats`, `/system/status`, `/system/https-info`, `/system/restart-mpv`, `/system/restart-dashboard`, `/system/restart-rpi` | Diagnostics, support scripts, operator refresh flows | `rpi_dashboard/services/system.py` and supported restart endpoints | Compatibility only | Legacy JSON marker + route hit logging | Restore the inline system branches |
| `/youtube/cookies/status`, `/youtube/age-check`, `/media/preview` | WebUI player preview, admin diagnostics | `rpi_dashboard/services/player.py` / YouTube helpers | Compatibility only | Legacy JSON marker + route hit logging | Restore the inline preview helpers |
| `/keepalive` | Audio route keepalive actions | `rpi_dashboard/services/audio.py` keepalive helpers | Compatibility only | Legacy JSON marker + route hit logging | Restore the inline keepalive branch |

## Duplicate headless surface

`python tui.py --headless` currently owns its own aiohttp route set and must remain test-compatible for now. Target replacement is a shared registry-backed headless mode that reuses the same route handlers as the production API.

## Acceptance checkpoints

- All consumers in `rpi_dashboard/static/js/app.js`, tests, and docs are migrated to replacement routes first.
- Legacy endpoints keep a clear compatibility response until each replacement is verified.
- Removal happens only after the route group has a documented rollback and no in-repository consumers remain.
