## 2026-06-19 - Added ARIA labels to web UI icon-only buttons
**Learning:** Found several icon-only buttons (like ⏸, ⏹, ⏪10, 10⏩, 🔉, 🔊, 🔇, and CEC navigation buttons) lacking `aria-label`s, rendering them unreadable to screen readers.
**Action:** Always verify that buttons containing only symbols or emojis have descriptive `aria-label` attributes.

## 2026-06-20 - Redesigned Audio Mixer with animated lines and a11y improvements
**Learning:** Found that static dashed lines in the audio mixer were difficult to read. Also discovered that screen readers couldn't understand the `<svg>` visualization of active routes.
**Action:** Replaced static lines with flowing animated `<path>` elements. Added a `sr-only` class text summary element that accurately reads out all active paths. Ensure `aria-hidden="true"` is applied on purely decorative SVG representations so screen readers do not try to parse complex nodes.

## 2026-07-27 - Dynamic Vanilla JS UI Element Accessibility
**Learning:** Discovered that dynamically generated UI elements in Vanilla JS (like theme toggles and tooltips) can silently fail to render if attached to non-existent DOM containers, and frequently lack proper internationalized aria-labels when containing raw visual characters.
**Action:** Always ensure dynamic UI elements attach to guaranteed existing containers (e.g., `#lang-switch`), wrap visual characters in `<span aria-hidden="true">`, and assign dynamic translations using properties like `dataset.i18nAriaLabel` rather than static `aria-label` attributes to remain accessible to screen readers across languages.
