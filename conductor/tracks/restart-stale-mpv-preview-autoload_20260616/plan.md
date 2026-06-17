# Implementation Plan: Restart stale mpv and automatic player preview

## Phase 1 — Diagnostics
- [x] Reproduce/inspect stale mpv detection gap
- [x] Define safe stop behavior for live vs stale mpv

## Phase 2 — Backend fixes
- [x] Add helpers to discover mpv processes by dashboard socket signature
- [x] Make `/mpv/status` report IPC/pgrep-discovered mpv
- [x] Make `/system/restart-mpv` stop stale/orphan mpv and clean stale sockets
- [x] Make restart endpoints return truthful systemctl results

## Phase 3 — Player UX fixes
- [x] Remove manual Paste clipboard and Preview buttons
- [x] Auto-detect clipboard media URL on Player entry
- [x] Auto-preview typed/pasted/direct URLs

## Phase 4 — Validation
- [x] Update tests for restart and automatic preview/clipboard behavior
- [x] Run local CI and Conductor finish pipeline
- [x] Run `tools/verify-done.sh`
