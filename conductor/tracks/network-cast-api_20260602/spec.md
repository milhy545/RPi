# Specification: Network Cast API (Port 8099)

## Overview
Create a lightweight local network listener (HTTP server) running on port 8099 that receives media URLs and triggers the media player (`mpv`), while temporarily suspending the core TUI.

## Functional Requirements
- HTTP server listening on `0.0.0.0:8099`.
- Endpoint `/play` accepting POST requests with a URL payload.
- Subprocess manager to launch `mpv` (with `yt-dlp` support).
- TUI Suspend/Resume mechanism (pause TUI rendering and release terminal control while media is playing).

## Non-Functional Requirements
- Zero-latency response to network requests.
- Extremely low memory footprint (e.g., using Python's built-in `http.server` or a minimal async framework).

## Out of Scope
- Full WebUI interface (only the API backend for now).
