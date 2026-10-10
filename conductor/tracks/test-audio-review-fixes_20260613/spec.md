# Spec: Test Audio Review Fixes

## Goal
Apply small, layout-preserving fixes discovered during the Test Audio WebUI review and E2E pass.

## Requirements
- Preserve the approved Test Audio layout: output sinks on the left, input sources on the right.
- Do not replace the stable Audio tab.
- Keep all fixes inside existing behavior and labels.
- Source cards must call source volume/mute APIs, not sink APIs.
- DLNA keepalive badge must represent DLNA keepalive only, not unrelated Bluetooth keepalive.
- Connected badges must use existing badge styling.
- Keepalive process launch must avoid shell interpolation of sink names.
- Latency label must match the backend mpv `audio-delay` behavior.

## Acceptance Criteria
- Safe Test Audio API E2E checks pass.
- Extracted WebUI JavaScript passes `node --check`.
- Python syntax compilation passes for touched files.
- Live `/selftest/testaudio` returns `ok: true`.
