# Design Reference: Bluetooth Control Center

## Source

- `docs/design/rpi-screenshots/RPi-BT-TUI.png`
- `docs/design/bluetooth/bt-webui-gemini-prototype.html`

## TUI Visual Inventory

The reference is a dense terminal dashboard, not a simple settings form.

Top bar:

- Bluetooth marker at far left.
- `RPi Bluetooth Control Center (TUI)`.
- `Dual Adapter Management`.
- Right command strip: auto connect, scan all, pair new, refresh, quit.

Topology:

- One large framed panel titled `TOPOLOGY`.
- Cyan left half for Adapter A.
- Green right half for Adapter B.
- Adapter A is audio-oriented.
- Adapter B is IO/controllers-oriented.
- Multiple grouped device boxes connect into adapter hubs.
- A legend row separates topology from tables.

Middle row:

- Adapter A devices table.
- Adapter B devices table.
- Available devices table.
- Quick actions command list.

Bottom row:

- Adapter status.
- Diagnostics.
- Recent events.
- Help.

Footer:

- Bluetooth service status.
- total connected and paired.
- OS, CPU, memory.

## Implementation Interpretation

Textual should reproduce the structure and information hierarchy. Exact glow effects, pixel line routing, and high-fidelity icon art are not required. Fixed-width terminal clarity is required.

Use color semantics consistently:

- cyan: Adapter A / audio side / strong path;
- green: Adapter B / IO-controller side / running/connected;
- yellow: available/weak/warning;
- red: disconnected/error;
- white/gray: neutral labels and values.

Prefer ASCII-safe symbols in live tty sections:

- `BT` instead of decorative Bluetooth glyph if tty output is unreliable;
- `|--`, `---`, `x`, `[S]`, `[P]`, `[R]` for stable line grammar;
- Textual borders are acceptable if current tty tests show readable output.

## Fidelity Checklist

- [x] Header matches reference content.
- [x] Topology is one large full-width framed region.
- [x] Adapter A and B hubs are visually distinct.
- [x] Device category boxes exist even with empty live data.
- [x] Legend appears below topology.
- [x] Middle and bottom grids match reference panel names.
- [x] Quick actions and Help are visible without scrolling.
- [x] Footer summarizes service/totals/system.
- [x] Physical tty capture remains legible.

## WebUI Visual Inventory

The saved Gemini prototype is the WebUI Bluetooth settings design reference. It is a standalone HTML prototype, not production-ready integration code.

Primary shell:

- dark-first `RPi Control Center` top navigation;
- Raspberry Pi identity at top left;
- central HCI status and topology legend;
- Basic/Expert segmented mode control;
- language and theme icon controls;
- Expert left sidebar with Bluetooth selected;
- Expert right sidebar for quick actions and summary.

Main content:

- advanced header `Správa Topologie Bluetooth`;
- responsive grid using named areas;
- topology panel as the primary surface;
- control, filter, hardware status, and device detail panels below/alongside topology.

Topology behavior:

- fixed-size pan/zoom canvas inside a clipped panel;
- Adapter A cyan/audio hub;
- Adapter B green/IoT/input hub;
- selectable device nodes;
- SVG Bezier connection lines;
- offline dimming and dashed paths;
- zoom in, zoom out, reset controls.

Panels:

- service control toggles and select controls;
- view filters;
- Adapter A/B RSSI gauges;
- dynamic device detail;
- Expert quick action grid;
- Expert total summary cards.

## WebUI Implementation Interpretation

Preserve design and interaction shape. Change implementation details freely where required to make it production-grade:

- move static prototype data into backend-driven state;
- replace CDN scripts with repository-owned dependencies/assets;
- replace dynamic Tailwind class construction with stable CSS;
- keep all device operations adapter-aware;
- add real loading, empty, degraded, and error states;
- keep Basic mode useful on smaller screens;
- keep Expert mode dense and operational, not marketing-like.

## WebUI Fidelity Checklist

- [x] Visual shell matches the prototype in dark mode.
- [x] Basic and Expert modes match the prototype behavior.
- [x] Topology pan, zoom, reset, selection, offline dimming, and line colors work.
- [x] Adapter A remains cyan/audio-oriented.
- [x] Adapter B remains green/IO-controller-oriented.
- [x] Control, filter, hardware, detail, quick-action, and summary panels are present.
- [x] Live backend state replaces prototype sample devices without changing composition.
- [x] Browser E2E screenshots are reviewed against the saved prototype.
