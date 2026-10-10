# Specification: Player paste button inside URL input

## Overview
Correct the Player URL row layout: the manual paste control must appear inside the URL input area at the right edge, before the quality selector. It must show a single paste icon, while automatic clipboard import and 720p default remain unchanged.

## Requirements
- Paste control is visually inside the URL input field, not after the quality selector.
- Paste control has a single icon, no duplicated icon/text.
- Quality selector remains immediately after the URL input wrapper.
- Manual paste overwrites current URL and triggers preview.
- Automatic clipboard import remains enabled and does not overwrite current URL.
- Default quality remains 720p.
- Real WebUI verification with remote Playwright screenshot is mandatory before completion.

## Acceptance Criteria
- Screenshot/DOM verification proves the paste button is inside the URL input wrapper and left of the quality selector.
- No duplicate paste icon in rendered button text.
- Existing tests and finish pipeline pass.
- `tools/verify-done.sh` passes.
