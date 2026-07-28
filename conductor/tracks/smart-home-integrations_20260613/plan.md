<Implementation Plan: Smart Home Integrations>
## Background
The RPi currently has a full REST API for media playback (mpv), CEC control, audio routing, and system stats. The physical Alexa AUX routing via PipeWire loopback is already complete. The user has decided to prioritize Home Assistant (HA) integration via REST and MQTT, while deferring Alexa and Google Home cloud skills. The HA server runs at 192.168.0.58 on the same LAN, and RPi is at 192.168.0.205. The goal is to provide HA entities (media player, switches, sensors) through REST templates and subsequently build a lightweight MQTT bridge for real-time state updates without polling.

## Phase 1: HA REST Integration
- [ ] Task: Create `src/smart_home/ha_configuration.yaml` defining Home Assistant entities: `media_player.rpi_tv`, `switch.rpi_tv_power`, and `sensor.rpi_tv_system` utilizing the existing REST API endpoints.
- [ ] Task: Create `src/api/routes/smart_home.py` with function `get_ha_config()` to serve the `/ha/config` endpoint, returning the parsed or raw contents of `src/smart_home/ha_configuration.yaml`.
- [ ] Task: Update `src/api/main.py` to import the router from `src/api/routes/smart_home.py` and register it with the main API application.
- [ ] Verify: `curl -s http://localhost:8090/ha/config | grep media_player.rpi_tv`

## Phase 2: MQTT Event Bridge
- [ ] Task: Add `paho-mqtt` to dependencies in `pyproject.toml`.
- [ ] Task: Create `src/smart_home/mqtt_client.py` with an `MQTTBridge` class that initializes a lightweight connection using a configurable broker address from the `MQTT_BROKER_URL` environment variable.
- [ ] Task: Implement `MQTTBridge.subscribe_commands()` in `src/smart_home/mqtt_client.py` to subscribe to `rpi-tv/player/command` and `rpi-tv/cec/command`, routing received payloads to internal API controllers.
- [ ] Task: Update the player status hook in `src/mpv/player.py` (e.g., `MpvPlayer.on_status_change`) to publish JSON state changes to `rpi-tv/player/status`.
- [ ] Task: Update `AudioRouter.set_state` in `src/audio/router.py` to publish current routing state to `rpi-tv/audio/state` whenever the audio route changes.
- [ ] Task: Add a telemetry loop `publish_system_stats()` in `src/system/monitor.py` to publish system stats periodically to `rpi-tv/system/stats`.
- [ ] Verify: `uv run python -c "import paho.mqtt.client; print('paho-mqtt installed')"`

## Phase 3: Cloud Voice Skills
- [ ] Task: Configure public HTTPS endpoint via Cloudflare Tunnel or Nabu Casa [DEFERRED — after all current tracks close]
- [ ] Task: Implement Alexa Smart Home Skill linking HA entities [DEFERRED — after all current tracks close]
- [ ] Task: Implement Google Home Action [DEFERRED — after all current tracks close]
- [ ] Verify: `echo "Phase 3 deferred"`

## Acceptance Criteria
- [ ] Home Assistant configuration YAML is successfully exposed on `/ha/config`
- [ ] MQTT bridge connects using `MQTT_BROKER_URL`, and publishes topics without memory leaks (within 1GB RAM constraint)
- [ ] All existing tests pass: `uv run python -m pytest -q`
- [ ] Lint passes: `uv run ruff check .`
- [ ] `tools/verify-done.sh` passes
</Implementation Plan: Smart Home Integrations>
