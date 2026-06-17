# Specification: Player paste button and 720p default

## Overview
Keep automatic clipboard URL detection, but add a manual paste button directly in the Player URL row next to the quality selector. The manual button should be user-gesture friendly and overwrite the current URL when requested. Change default playback quality from 360p to 720p.

## Requirements
- Default quality selector and playback default must be 720p.
- Player URL row must include a compact paste button next to the quality selector.
- Manual paste button must read clipboard during user activation and overwrite any existing URL.
- Automatic clipboard import must remain enabled but must not overwrite an existing URL.
- Preview must continue to update automatically after auto or manual paste.

## Acceptance Criteria
- `DQ` is 720p and the 720p option is selected by default.
- HTML contains the URL input, quality selector, and paste button in the same row.
- No separate standalone Preview button is reintroduced.
- Tests and CI pass.
