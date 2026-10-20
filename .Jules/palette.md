## 2026-06-19 - Added ARIA labels to web UI icon-only buttons
**Learning:** Found several icon-only buttons (like ⏸, ⏹, ⏪10, 10⏩, 🔉, 🔊, 🔇, and CEC navigation buttons) lacking `aria-label`s, rendering them unreadable to screen readers.
**Action:** Always verify that buttons containing only symbols or emojis have descriptive `aria-label` attributes.

## 2026-06-20 - Redesigned Audio Mixer with animated lines and a11y improvements
**Learning:** Found that static dashed lines in the audio mixer were difficult to read. Also discovered that screen readers couldn't understand the `<svg>` visualization of active routes.
**Action:** Replaced static lines with flowing animated `<path>` elements. Added a `sr-only` class text summary element that accurately reads out all active paths. Ensure `aria-hidden="true"` is applied on purely decorative SVG representations so screen readers do not try to parse complex nodes.

## 2026-06-21 - Added internationalized ARIA labels to modal close buttons
**Learning:** Found that modal close buttons containing only the '×' character were missing `aria-label` attributes, making them inaccessible to screen readers. Adding static `aria-label` attributes breaks internationalization.
**Action:** Applied the `data-i18n` and `data-i18n-attr="aria-label"` pattern to visually hidden UI elements containing static visual icons like '×'. This translates accessibility text for screen readers without replacing the visual element.
