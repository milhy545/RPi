# Specification: Player clipboard autoload reliability

## Overview
Improve automatic clipboard URL insertion for the Player tab. Browsers may block clipboard reads on page load, so the UI must retry on safe user/browser events without reintroducing manual paste buttons.

## Requirements
- Keep Player free of manual clipboard/preview buttons.
- Attempt clipboard URL import when Player opens.
- Retry clipboard URL import on user activation, window focus, and visibility return while Player input is empty.
- Preserve automatic preview for any `http(s)` URL.
- Do not overwrite an existing Player URL.

## Acceptance Criteria
- User normally does not need to paste manually after opening/clicking into the Player tab when browser permission allows clipboard read.
- If browser blocks clipboard on initial load, later user activation retries automatically.
- Existing WebUI tests pass.
