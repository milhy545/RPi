# Stale Tracks Audit

## Summary Table

| Track | Verdict | Implemented | Missing | Recommended action |
|---|---|---:|---:|---|
| bt-audio-loopback_20260611 | done | runtime route, start/stop/status, USB detection, BT detection, module tracking, duplicate prevention, persistence checks | none blocking | closed in current stack |
| audio-routing-mixer-v2_20260613 | done / merged | audio backend endpoints, sink/source classification, mixer UI, latency controls, stable layout | true DLNA renderer/input implementation lives in other tracks | closed in stable Audio |
| automated-provisioning_20260602 | done | provisioning scripts, uv/yt-dlp setup, service template, idempotent install pieces | historical only; current live stack supersedes it | baseline preserved |
| network-cast-api_20260602 | done / merged | 8099 HTTP server, play endpoints, mpv manager, low-memory design, TUI suspension pieces | original API shape is superseded | closed in WebUI and mode-switcher |
| mode-switcher-engine | done | suspend/resume engine, subprocess spawning, log buffer, watchdog, signal handling, API rejection while active | UI parity leftovers live elsewhere | core engine closed |

## Notes

- This audit is read-only and reflects the current repository state.
- Tracks marked "merged" are effectively complete in the newer architecture, even if their original track scope was superseded.
- Tracks marked "partial" should not be expanded blindly; they need scope reduction or a successor track.
