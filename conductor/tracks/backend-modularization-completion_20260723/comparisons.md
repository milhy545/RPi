# Phase 3 Comparison — backend-modularization-completion_20260723

Measured locally on the Pi with the current `main` branch and the phase baseline commit `00495e12e0e07728ce2ad3e62ad502649a20d3de`.

## Route ownership

| Metric | Baseline | Current |
|---|---:|---:|
| API route registrations | 98 | 98 |
| Routes still mapped to `legacy_webserver_endpoint` | 24 | 0 |
| Legacy route list | `/cec/br/st`, `/cec/br/start`, `/cec/br/stop`, `/cec/in`, `/cec/key`, `/cec/send`, `/devices`, `/devices/bt/scan`, `/dlna/connect`, `/dlna/disconnect`, `/dlna/renderer/start`, `/dlna/renderer/status`, `/dlna/renderer/stop`, `/dlna/scan`, `/dlna/select`, `/media/preview`, `/system/https-info`, `/system/hw-stats`, `/system/restart-dashboard`, `/system/restart-mpv`, `/system/restart-rpi`, `/system/status`, `/youtube/age-check`, `/youtube/cookies/status` | none |

## Runtime samples

| Metric | Baseline | Current |
|---|---:|---:|
| Startup (ms) | 13.7 | 12.7 |
| RSS (KiB) | 39556 | 33356 |
| CPU (%) | 17.2 | 11.8 |
| Sample core (psr) | 0 | 2 |

## Endpoint latency samples

| Route | Baseline ms | Current ms |
|---|---:|---:|
| `/system/hw-stats` | 398.7 / 395.8 / 390.4 | 383.8 / 385.3 / 370.5 |
| `/system/status` | 440.0 / 419.7 / 420.0 | 440.3 / 440.0 / 372.8 |
| `/devices/state` | 3020.1 / 3122.6 / 2789.9 | 3003.1 / 3072.6 / 3056.9 |

## Polling surface

| Metric | Baseline | Current |
|---|---:|---:|
| `setInterval(` | 2 | 2 |
| `setTimeout(` | 65 | 65 |
| `requestAnimationFrame(` | 0 | 0 |

## Notes

- Route ownership is the main win: the compatibility registry no longer exposes legacy markers.
- Startup and memory are at least stable in this sample.
- Polling surface did not grow.
- Latency remains dominated by the underlying device/system commands, not route dispatch.
