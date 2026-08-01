# Project Health Audit - 28 July 2026

## Scope and Verdict

This audit covers Git history, Conductor state, application architecture, automated checks, security tooling, the production RPi runtime, and live WebUI behaviour at commit `638caa4`.

The dashboard is operational and substantial backend modularisation has occurred, but the repository is **not in a completed or release-ready state**. The final bulk commit closed tracks without satisfying their own plans, introduced a test deadlock, and did not implement the promised unified WebUI refactor. Production is serving the current files, so the unchanged interface is not a deployment or browser-cache problem.

| Area | Score | Evidence-based assessment |
| --- | ---: | --- |
| Runtime and core features | 6/10 | Service is active; player, audio, Bluetooth, devices and most APIs respond. |
| Backend architecture | 5/10 | Route/service extraction is real, but large compatibility monoliths remain. |
| WebUI and responsive UX | 3/10 | Duplicate navigation/status surfaces, dead telemetry, blank Terminal tab and recurring JS errors. |
| Audio refactor | 4/10 | Some APIs and routing exist; planned package split, master UI and TUI work do not. |
| Tests and CI | 3/10 | 324 tests pass when one deadlocking test is excluded; only 58% package coverage. |
| Security and operations | 4/10 | LAN/Tailscale allow-list exists, but unauthenticated control remains broad and one dependency is vulnerable. |
| Conductor governance | 2/10 | Registry completion state contradicts plans, metadata, CI and runtime evidence. |

## What Actually Changed

Commits on 27 July made useful changes: legacy audio, player, device, CEC and system routes were delegated into `rpi_dashboard/services/` and `rpi_dashboard/api/`; Network, System and Logs panels were added; and return-to-dashboard controls gained API/UI work.

The final `638caa4` commit changed 46 files (`+1,174/-517`), but much of that was plans, track status and supporting files. Its WebUI change was only a 46-line token file, eight HTML lines for the theme/PWA, and 24 JavaScript lines for status telemetry. It did not remove the Bluetooth sub-header/footer or redesign the page. The visible Audio topology predates it (`1792d56` and `61cd086`, 25 July).

## Critical Findings

1. **Conductor tracks were closed administratively, not verified.** The unified UI track was created and marked complete in the same commit while all 24 tasks remained unchecked. The audio track has 43 unchecked items and metadata still says `active`. Eight other registry-complete tracks also retain 13-33 unchecked tasks. No valid completion receipt exists for `638caa4`.
2. **Final CI never passed.** GitHub run `30326330766` was cancelled at its 15-minute timeout while running pytest. Locally, `test_return_config_get_set` deadlocks because `update_config()` holds a non-reentrant lock and calls two helpers that acquire the same lock. Excluding it gives `324 passed, 1 deselected` in 33 seconds.
3. **The promised WebUI refactor is absent.** Live desktop and mobile checks reproduce both global and Bluetooth Basic/Expert/language controls and two adjacent status bars. `theme.css` is largely unused; the CSS still contains hundreds of hard-coded colours and pixel values.
4. **The global status bar cannot update.** JavaScript targets `status-cpu`, `status-ram` and `status-temp`, while the DOM defines `sb-cpu` and `sb-ram` only. Polling starts only after manually enabling System live monitoring. Production therefore remains at `CPU: --` and `RAM: --`.
5. **The extracted WebUI has a blank Terminal tab.** `rpi_dashboard/static/index.html` has a Terminal navigation button but no `p-terminal` panel. Its JavaScript also opens the WebSocket without fetching or sending the required token. The embedded fallback HTML contains a different implementation, demonstrating source drift.
6. **A recurring JavaScript exception runs every three seconds.** `updBr()` writes to removed `brb`/`brs` elements without null checks. A live session accumulated more than 100 console errors.

## Architecture, Quality, and Security

The main remaining files are too large for reliable ownership: `webserver.py` is 3,088 lines, `tui.py` 2,674, Bluetooth BlueZ/service modules 1,337/1,220, audio `__init__.py` 1,054, and `app.js` 915. The audio “split” mostly renamed the old monolith into a package; planned `state.py`, `mixer.py`, `matrix.py`, `multi_output.py`, `profiles.py` and related modules do not exist.

Ruff reports an unused import in `tests/test_pwa.py`. Mypy reports five errors across audio, smart-home and TUI code. Package coverage is 58%, with particularly weak coverage in media (15%), audio DLNA (17%), audio routing (20%), player (35%) and system (38%). The live `/system/status` endpoint returns HTTP 500, although `/system/hw-stats`, `/audio/state`, `/bt/state` and `/ha/config` respond.

`pip-audit` finds CVE-2026-55404 in `yt-dlp 2026.6.9`, fixed in `2026.7.4`. The vulnerable shortcut-writing options are not used here, which reduces immediate reachability but does not remove the upgrade requirement. Bandit reports no high-severity issue, 14 medium and 307 low findings; the medium set is mostly fixed `/tmp` paths, all-interface binds and URL scheme validation. `SECURITY.md` remains an unedited template with fictitious supported versions. Tracked backup files and processed runtime reports add avoidable noise.

## Recommended Recovery Order

1. Reopen every registry-complete track whose plan, metadata, receipt or verification disagrees; treat `638caa4` as an unverified partial implementation.
2. Fix the return-service lock deadlock, restore a full pytest pass, fix Ruff/mypy, and require those checks in GitHub CI before accepting further feature work.
3. Repair the blank Terminal panel/auth flow, `updBr()` errors, `/system/status`, and global telemetry binding.
4. Execute the unified WebUI track visibly: remove Bluetooth-owned global controls/footer, integrate theme tokens, and verify desktop/mobile screenshots and interactions.
5. Re-scope the audio track into small verified phases. Do not call a file rename modularisation; split responsibilities and add the missing master-volume/TUI behaviour with tests.
6. Upgrade `yt-dlp`, replace `SECURITY.md`, remove tracked backups/runtime artefacts, and define an explicit authentication policy for control endpoints.

## Verification Record

- Production hashes for `index.html`, `app.js`, `main.css` and `theme.css` match the current checkout.
- Full pytest: hangs at `test_return_config_get_set`; remaining suite: `324 passed, 1 deselected`.
- Coverage: 58%; Ruff: 1 error; mypy: 5 errors; `node --check`: pass.
- Playwright: desktop/mobile duplicate controls confirmed; Audio inspected; Terminal blank; recurring console exception confirmed.
- `tools/verify-done.sh`: fails because `638caa4` has no successful exact-main receipt. The working tree also contains this audit and contributor-guide update.

