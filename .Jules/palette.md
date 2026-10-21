## 2026-06-19 - Added ARIA labels to web UI icon-only buttons
**Learning:** Found several icon-only buttons (like ⏸, ⏹, ⏪10, 10⏩, 🔉, 🔊, 🔇, and CEC navigation buttons) lacking `aria-label`s, rendering them unreadable to screen readers.
**Action:** Always verify that buttons containing only symbols or emojis have descriptive `aria-label` attributes.

## 2026-06-20 - Redesigned Audio Mixer with animated lines and a11y improvements
**Learning:** Found that static dashed lines in the audio mixer were difficult to read. Also discovered that screen readers couldn't understand the `<svg>` visualization of active routes.
**Action:** Replaced static lines with flowing animated `<path>` elements. Added a `sr-only` class text summary element that accurately reads out all active paths. Ensure `aria-hidden="true"` is applied on purely decorative SVG representations so screen readers do not try to parse complex nodes.

## 2026-10-21 - Added aria-labels to modal close buttons
**Learning:** Modal close buttons containing only the '×' symbol lacked `aria-label`s, making them unreadable to screen readers. I discovered the app uses a custom `data-i18n="key"` and `data-i18n-attr="aria-label"` system to translate the text in the `app.js` instead of overwriting innerText for translated aria labels, which requires adding them to `I18N` and `ariaText`.
**Action:** When adding accessible labels to UI elements that have static visual icons, use the `data-i18n` framework and update `I18N` mappings in `app.js` rather than adding static English `aria-label` attributes.
