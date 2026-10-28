## 2026-06-19 - Added ARIA labels to web UI icon-only buttons
**Learning:** Found several icon-only buttons (like ⏸, ⏹, ⏪10, 10⏩, 🔉, 🔊, 🔇, and CEC navigation buttons) lacking `aria-label`s, rendering them unreadable to screen readers.
**Action:** Always verify that buttons containing only symbols or emojis have descriptive `aria-label` attributes.

## 2026-06-20 - Redesigned Audio Mixer with animated lines and a11y improvements
**Learning:** Found that static dashed lines in the audio mixer were difficult to read. Also discovered that screen readers couldn't understand the `<svg>` visualization of active routes.
**Action:** Replaced static lines with flowing animated `<path>` elements. Added a `sr-only` class text summary element that accurately reads out all active paths. Ensure `aria-hidden="true"` is applied on purely decorative SVG representations so screen readers do not try to parse complex nodes.

## 2026-07-28 - Removed static aria-label from icon-only buttons
**Learning:** Some icon-only buttons in `index.html` (like `aria-label="English"`) used hardcoded English aria-labels which defeat internationalization. Additionally, emojis/unicode icons inside these buttons were not wrapped in `<span aria-hidden="true">`, which can cause screen readers to read the visual character and the aria-label.
**Action:** Always wrap visual icons/emojis in `<span aria-hidden="true">`, use `data-i18n` + `data-i18n-attr="aria-label"` to set accessible labels dynamically for i18n.
