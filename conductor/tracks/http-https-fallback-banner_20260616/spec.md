# Specification: HTTP fallback with HTTPS clipboard banner

## Overview
Keep `http://rpi/` as a real fallback without automatic redirect, but make the secure HTTPS path obvious for clipboard support.

## Requirements
- Do not redirect HTTP to HTTPS.
- On HTTP pages, show a visible banner explaining that HTTPS is needed for clipboard paste.
- The HTTP banner must include an `Open HTTPS` button/link to the matching HTTPS URL.
- On HTTPS pages, show a small secure status indicating clipboard secure context is enabled.
- Preserve existing layout and Player controls.
- Verify with remote browser testing over both HTTP and HTTPS.

## Acceptance Criteria
- `http://rpi/` displays the fallback banner and an `Open HTTPS` link to `https://rpi/`.
- `https://rpi/` displays secure clipboard status and no fallback warning.
- No automatic redirect occurs from HTTP.
- Remote Playwright verifies both states.
- CI and `tools/verify-done.sh` pass.
