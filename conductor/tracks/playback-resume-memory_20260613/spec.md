# Specification: Playback Resume Memory

## Goal
Remember the last playback position when a video is interrupted before the natural end, and offer the user a WebUI prompt to resume from that position when the same video is played again.

## Problem
If mpv playback is interrupted accidentally or intentionally before video end, the current position is lost. The user wants WebUI to offer "Continue from HH:MM:SS" on the next play of the same URL/video.

## Requirements
1. **Track playback progress** while mpv is active via IPC (`/tmp/rpi-mpv.sock`).
2. **Persist position** to a small JSON state file, e.g. `~/rpi-dashboard/playback-memory.json`.
3. **Only save interrupted playback**, not natural end:
   - Save if stopped/killed/replaced before completion.
   - Do not offer resume if position is near end (e.g. >95% or <30 seconds remaining).
4. **Match by stable media identity**:
   - YouTube video ID if available.
   - Otherwise normalized URL hash.
5. **WebUI prompt**:
   - When user enters/plays a known video, offer: `Continue from 12:34?`.
   - Buttons: `Resume`, `Start over`, `Forget`.
6. **Safe mpv protection**:
   - Before restarting/stopping/replacing mpv, query and persist `time-pos`, `duration`, `media-title`, URL/video ID.
7. **Low overhead**:
   - Poll no more than once per 3-5 seconds while mpv is active.
   - JSON file small and human-readable.

## Data Model
```json
{
  "dQw4w9WgXcQ": {
    "id": "dQw4w9WgXcQ",
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "title": "Rick Astley - Never Gonna Give You Up",
    "position": 73.4,
    "duration": 213.0,
    "updated_at": "2026-06-13T05:00:00Z",
    "reason": "interrupted"
  }
}
```

## Acceptance Criteria
- [ ] While a video is playing, current position is periodically saved.
- [ ] If playback is stopped before 95%, WebUI offers resume next time.
- [ ] If playback reaches natural end, resume memory is cleared/ignored.
- [ ] Resume starts playback and seeks to stored position.
- [ ] Start over clears/ignores stored position and plays from 0.
- [ ] Forget removes stored memory for that video.
- [ ] E2E test verifies interrupt → resume prompt → resume seek works.
