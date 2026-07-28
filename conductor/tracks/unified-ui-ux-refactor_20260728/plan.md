# Implementation Plan: Unified UI/UX Refactor & Theme Engine

## Background
The user requested a massive global refactor of both the WebUI and TUI to bring them into absolute parity (as much as the CLI allows) and to modernize the entire look based on the Bluetooth tab's design language. 
Currently, the WebUI is not compact enough for mobile/tablet, the BT tab has duplicated elements (double language bars, double status bars), and the status bar is static/dead (CPU values never update). Additionally, the UI needs a robust foundational CSS architecture (a graphics/theme engine) using CSS variables so future skins, themes, and plugins can be added effortlessly.

## Phase 1: CSS Theme Engine & Cleanup
- [ ] Task: Create `rpi_dashboard/static/css/theme.css` and define a comprehensive set of CSS variables (`:root`) for colors, spacing, typography, and component states (inspired by the BT tab).
- [ ] Task: Remove all hardcoded colors and pixels from `rpi_dashboard/static/css/style.css` and replace them with the new CSS variables.
- [ ] Task: Remove the duplicated top language bar and the duplicated status bar from the BT tab HTML and JS templates.
- [ ] Verify: `uv run ruff check .`

## Phase 2: Active Status Bar & Telemetry Binding
- [ ] Task: Update `rpi_dashboard/static/js/app.js` to implement a periodic polling mechanism (or WebSocket listener) that fetches data from `/system/stats`.
- [ ] Task: Bind the fetched CPU, RAM, and Temperature values directly to the DOM elements in the global status bar so they update in real-time.
- [ ] Task: Ensure the status bar displays loading states or `--` when the backend is unreachable.
- [ ] Verify: `uv run python -m pytest -q`

## Phase 3: Global WebUI Redesign (Mobile-First & Compact)
- [ ] Task: Refactor the main layout grid in `index.html` to be significantly more compact on mobile and tablet screens using CSS Grid/Flexbox and media queries.
- [ ] Task: Apply the BT-tab inspired modern design (glassmorphism, subtle borders, active states) globally to the Player, Audio, Network, and System tabs.
- [ ] Task: Optimize touch targets for "smart" user friendliness (e.g., larger tap areas but tighter visual grouping).
- [ ] Verify: `tools/verify-done.sh`

## Phase 4: TUI Visual Parity
- [ ] Task: Update `tui.py` Textual layout to mirror the new WebUI compact structural grid.
- [ ] Task: Apply Textual CSS (`.tcss`) to mimic the WebUI's theme colors, borders, and active states.
- [ ] Task: Ensure the TUI status bar (Header/Footer) correctly binds to the same real-time system stats (CPU/RAM/Temp) as the WebUI.
- [ ] Verify: `uv run python tui.py --headless` (dry-run check)

## Acceptance Criteria
- [ ] CSS Theme engine is fully tokenized via CSS variables.
- [ ] No duplicated status bars or language bars exist on any tab.
- [ ] The WebUI status bar actively updates CPU/RAM/Temp values without page reload.
- [ ] The WebUI is highly compact and usable on mobile/tablet resolutions.
- [ ] The TUI layout and color scheme matches the WebUI structure.
- [ ] All existing tests pass: `uv run python -m pytest -q`
- [ ] Lint passes: `uv run ruff check .`
- [ ] `tools/verify-done.sh` passes
