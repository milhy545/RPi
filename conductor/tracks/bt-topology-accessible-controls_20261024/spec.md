# Track Spec: Bluetooth Topology Accessible Controls

## Goal
Give the Bluetooth topology zoom and reset icon buttons clear Czech and English accessible names.

## Requirements
- Translate the accessible names when the WebUI language changes.
- Keep the existing icons, layout, and button actions unchanged.
- Cover both languages with a browser-level regression check.

## Acceptance Criteria
- Zoom in, zoom out, and reset controls expose the correct Czech and English `aria-label`.
- The visible `＋`, `−`, and `⛶` glyphs remain unchanged after language switching.
- Focused checks and the repository `github-safe` validation pass.
