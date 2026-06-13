# Specification: Git Live Development Workflow

## Goal
Make the live RPi working tree (`~/rpi-dashboard`) a real Git repository while preserving the existing GitHub history from Milhy-PC (`/home/milhy777/Develop/RPi`). RPi is the live development/test environment; Milhy-PC remains the GitHub push/review gateway.

## Requirements
- Preserve existing Git history from Milhy-PC.
- Do not track runtime secrets or volatile files (`yt-cookies.txt`, `.venv`, `__pycache__`, `rootfs`, browser profiles, logs).
- Commit the current RPi live source state atomically.
- Add a Milhy-PC remote named `rpi` pointing to the RPi repo.
- Keep GitHub push workflow on Milhy-PC.
- Do not interrupt active mpv playback during setup.

## Acceptance Criteria
- [ ] `~/rpi-dashboard` is a Git repo with preserved history.
- [ ] `.gitignore` protects secrets and heavy runtime files.
- [ ] Current live source files are committed on RPi.
- [ ] Milhy-PC repo has remote `rpi`.
- [ ] Milhy-PC can fetch from RPi.
- [ ] Conductor registry updated.
