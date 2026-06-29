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

## User Feedback & Conductor Integration
The WebUI includes a feedback modal (accessible via the "Feedback" button in the topbar) allowing users to submit bug reports and feature requests.

- **Storage**: Feedback is sent as a `POST /report` JSON request, validated by the backend, and saved to the `reports/` directory.
- **Conductor Intake**: A systemd timer triggers the `tools/process_reports.py` worker every minute. This worker processes new reports, creates Conductor tracks (containing `spec.md` and a skeleton `plan.md`) under `conductor/tracks/`, and appends them to `conductor/tracks.md`.
