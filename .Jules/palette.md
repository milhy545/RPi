## 2026-06-19 - Added ARIA labels to web UI icon-only buttons
**Learning:** Found several icon-only buttons (like ⏸, ⏹, ⏪10, 10⏩, 🔉, 🔊, 🔇, and CEC navigation buttons) lacking `aria-label`s, rendering them unreadable to screen readers.
**Action:** Always verify that buttons containing only symbols or emojis have descriptive `aria-label` attributes.

## 2026-06-20 - Redesigned Audio Mixer with animated lines and a11y improvements
**Learning:** Found that static dashed lines in the audio mixer were difficult to read. Also discovered that screen readers couldn't understand the `<svg>` visualization of active routes.
**Action:** Replaced static lines with flowing animated `<path>` elements. Added a `sr-only` class text summary element that accurately reads out all active paths. Ensure `aria-hidden="true"` is applied on purely decorative SVG representations so screen readers do not try to parse complex nodes.

## 2026-06-21 - Modal Close Buttons Accessibility
**Learning:** Found that the "×" (times/multiply) character used for closing modals lacked ARIA labels, making it unintelligible to screen readers (which would read "multiply" instead of "Close"). We applied `data-i18n="close"` and `data-i18n-attr="aria-label"` to properly localize the screen reader text in both EN and CZ without altering the visual icon.
**Action:** Always ensure icon-only buttons in modals (and everywhere else) use localized `aria-label`s via the `data-i18n-attr` pattern.
