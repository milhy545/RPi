# Implementation Plan: Playback Resume Memory

## Phase 1: Backend State Model
- [~] Task: Add playback memory JSON helper functions
  - [ ] `load_playback_memory()`
  - [ ] `save_playback_memory()`
  - [ ] `media_key(url, meta)` using YouTube ID or URL hash
- [ ] Task: Add safe mpv state query helper
  - [ ] Query `time-pos`, `duration`, `media-title`, `pause`
  - [ ] Handle missing/dead socket gracefully

## Phase 2: Persist Interrupted Playback
- [ ] Task: Update `mpv_stop()` and `mpv_start()` replacement flow
  - [ ] Before stopping/replacing mpv, query current state
  - [ ] Save only if position is meaningful and not near end
- [ ] Task: Add periodic background position save while mpv active
  - [ ] Poll every 3-5 seconds
  - [ ] Avoid high CPU/RAM overhead

## Phase 3: WebUI Resume Prompt
- [ ] Task: Add API endpoint `GET /mpv/resume-info?url=...`
- [ ] Task: Add API endpoint `POST/GET /mpv/resume-forget?url=...`
- [ ] Task: Modify Play flow
  - [ ] If resume exists, show prompt with `Resume`, `Start over`, `Forget`
  - [ ] Resume calls `/mpv/play?...&resume=1`
  - [ ] Start over calls `/mpv/play?...&resume=0`

## Phase 4: Seek on Resume
- [ ] Task: After mpv starts, wait for IPC socket ready
- [ ] Task: Seek to stored position using `seek absolute`
- [ ] Task: Verify status shows expected position

## Phase 5: E2E & Safety
- [ ] Task: E2E: play video, wait 20s, stop, replay same URL → prompt appears
- [ ] Task: E2E: click Resume → playback starts near stored position
- [ ] Task: E2E: click Start over → starts from 0 and memory ignored
- [ ] Task: E2E: natural end does not show resume prompt
- [ ] Task: Conductor - User Manual Verification 'playback-resume-memory'
