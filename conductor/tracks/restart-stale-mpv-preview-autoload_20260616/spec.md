# Specification: Restart stale mpv and automatic player preview

## Overview
Fix WebUI restart controls so stale/orphan mpv processes that still hold DRM are detected and safely stopped. Refine Player UX so preview and clipboard import are automatic, without extra buttons.

## Functional Requirements
- `/mpv/status` must report live mpv discovered via IPC/pgrep even if the current webserver process did not spawn it.
- Restart mpv action must stop stale/orphan mpv processes using the dashboard IPC/socket signature, after saving resume memory when possible.
- Restart dashboard action must return real `systemctl` success/failure details.
- Player tab must automatically inspect clipboard on entry and insert a media URL when the input is empty.
- Player preview must load automatically when a URL is inserted or typed/pasted, including direct media URLs, not only YouTube.
- Remove dedicated Paste clipboard and Preview buttons from the Player controls.

## Acceptance Criteria
- Restart endpoints return truthful JSON with command return codes.
- Stale mpv processes holding `/tmp/rpi-mpv.sock` are included in status/stop flows.
- Player preview appears automatically for YouTube and direct media URLs.
- Clipboard import runs automatically on Player tab entry with permission-safe fallback.
- Existing WebUI layout and tabs are preserved.
- Local CI, finish-track pipeline, and `tools/verify-done.sh` pass.

## Out of Scope
- Changing tab layout or broad visual redesign.
- Replacing mpv playback pipeline.
