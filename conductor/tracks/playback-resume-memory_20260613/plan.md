# Implementation Plan: Playback Resume Memory

## Phase 1: Backend State Model
- [x] Task: Add playback memory JSON helper functions
  - [x] `load_playback_memory()`
  - [x] `save_playback_memory()`
  - [x] `media_key(url, meta)` using YouTube ID or URL hash
- [x] Task: Add safe mpv state query helper
  - [x] Query `time-pos`, `duration`, `media-title`, `pause`
  - [x] Handle missing/dead socket gracefully

## Phase 2: Persist Interrupted Playback
- [x] Task: Update `mpv_stop()` and `mpv_start()` replacement flow
  - [x] Before stopping/replacing mpv, query current state
  - [x] Save only if position is meaningful and not near end
- [x] Task: Add periodic background position save while mpv active
  - [x] Poll every 3-5 seconds
  - [x] Avoid high CPU/RAM overhead

## Phase 3: WebUI Resume Prompt
- [x] Task: Add API endpoint `GET /mpv/memory?url=...`
- [x] Task: Add API endpoint `GET /mpv/memory/clear?url=...`
- [x] Task: Modify Play flow
  - [x] If resume exists, show prompt with `Resume` / start over behavior
  - [x] Resume calls `/mpv/play?...&resume=1`
  - [x] Start over calls `/mpv/play?...&resume=0` after clearing memory

## Phase 4: Seek on Resume
- [x] Task: After mpv starts, wait for IPC socket ready
- [x] Task: Seek to stored position using `set_property time-pos`
- [x] Task: Verify status path is available after seek

## Phase 5: E2E & Safety
- [x] Task: Non-interrupting runtime smoke: stored URL → prompt data appears via `/mpv/memory`
- [x] Task: Non-interrupting monkeypatch E2E: Resume sends `set_property time-pos`
- [x] Task: E2E: Start over clears memory and plays from 0 behavior path
- [x] Task: Natural-end/near-end state does not show resume prompt via near-end filter
- [x] Task: Conductor - User Manual Verification 'playback-resume-memory'
