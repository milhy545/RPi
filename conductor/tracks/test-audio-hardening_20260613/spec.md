# Spec: Test Audio Hardening

## Goal
Harden the WebUI `Test Audio` tab without changing its approved layout or replacing the stable `Audio` tab.

## Requirements
- Keep the existing `Test Audio` layout: output sinks on the left, input sources on the right.
- Return JSON errors instead of HTTP 500 for invalid numeric audio inputs.
- Detect and manage orphan `pw-cat` keepalive loops after webserver restarts.
- Make DLNA latency controls internally consistent and user-readable.
- Escape dynamic WebUI values safely when inserted into HTML and JavaScript handlers.
- Add a safe self-test endpoint/script that validates the `Test Audio` tab without launching a heavy browser.
- Clean up stale orphan keepalive processes created by older sessions.

## Acceptance Criteria
- `/audio/volume` rejects non-numeric values with `ok: false` JSON.
- `/audio/latency` rejects non-numeric values with `ok: false` JSON.
- `/keepalive?action=status` reports live in-memory and orphan `pw-cat` keepalive targets.
- `/keepalive?action=stop_all` stops in-memory and orphan keepalive loops.
- WebUI JavaScript passes `node --check`.
- `/selftest/testaudio` returns `ok: true` on the live WebUI.
- Safe API E2E checks pass on `127.0.0.1:8099`.
