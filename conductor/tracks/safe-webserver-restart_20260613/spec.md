# Specification: Safe Webserver Restart Without Breaking mpv

## Goal
Allow restarting `webserver_8099.py` without breaking an already running mpv playback session or unlinking the active mpv IPC socket.

## Problem
The webserver currently unconditionally removes `/tmp/gfn-mpv.sock` on startup. If mpv is playing and the webserver restarts, the video may keep playing but WebUI loses control because the socket path is unlinked.

## Requirements
- Do not unlink `/tmp/gfn-mpv.sock` if a live mpv process is using it and the socket responds.
- Unlink stale socket only when no live/responsive mpv owns it.
- Startup must remain safe when no mpv is running.
- Restarting webserver must not stop mpv.

## Acceptance Criteria
- [ ] If no mpv is running, stale socket cleanup still works.
- [ ] If mpv is running and IPC responds, startup preserves the socket.
- [ ] Webserver starts normally after patch.
- [ ] `/mpv/status` still works after restart.
