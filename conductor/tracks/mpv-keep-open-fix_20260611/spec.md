# Specification: mpv --keep-open=always Fix

## Goal
Fix mpv socket freeze on video end by changing `--keep-open=yes` to `--keep-open=always`.

## Problem
- `--keep-open=yes`: Keeps mpv open after playback ends, but socket may freeze/become unresponsive
- `--keep-open=always`: Keeps mpv open AND pauses at end, socket remains responsive

## Root Cause
When video ends with `--keep-open=yes`, mpv enters a state where the IPC socket (`/tmp/gfn-mpv.sock`) stops responding to commands, requiring mpv restart.

## Solution
Change mpv launch command in `webserver_8099.py`:
```python
# Before
"--keep-open=yes"

# After
"--keep-open=always"
```

## Behavior Difference
| Flag | On Video End | Socket Status |
|---|---|---|
| `--keep-open=yes` | Stays open, shows last frame | May freeze |
| `--keep-open=always` | Pauses at last frame | Remains responsive |

## Acceptance Criteria
- [ ] mpv launches with `--keep-open=always`
- [ ] Video plays to end, pauses at last frame
- [ ] IPC socket remains responsive after video end
- [ ] Next play command works without mpv restart
- [ ] No socket freeze errors in logs