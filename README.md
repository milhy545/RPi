# Raspberry Pi Dumb TV Dashboard

Low-RAM Raspberry Pi TV dashboard for media playback, device control, and quick system management.

## Documentation
- [Documentation index](./docs/README.md)
- [Project overview](./docs/overview.md)
- [WebUI / API reference](./docs/webserver-8099.md)
- [Textual dashboard reference](./docs/tui.md)
- [Mode switcher reference](./docs/mode-switcher.md)
- [Multimedia keyboard daemon](./docs/keys2mpv.md)
- [Tests and verification](./docs/testing.md)
- [Operational playbooks](./docs/operations.md)

## Quick start
```bash
uv sync
uv run python tui.py
```

## Project layout
- `main.py` — minimal entry point
- `tui.py` — Textual dashboard
- `webserver.py` — WebUI, API, and terminal WebSocket server
- `mode_switcher.py` — foreground app supervision
- `keys2mpv.py` — multimedia keyboard daemon
- `conductor/` — product context, workflow, and tracks

### Security Notice
To avoid triggering automated scanners, the project follows strict rules against executing untrusted input via shell. Safe alternatives (like direct subprocess argument passing) are preferred.

### User Feedback & Conductor Integration
The RPi Dashboard includes a built-in user feedback system via the WebUI.
When a user submits a bug or feature request, it is saved locally to the `reports/` directory.
A background `report-processor` service scans these files and automatically generates draft Conductor tracks inside `conductor/tracks/` so that developers (and AI agents) can investigate and implement them.
