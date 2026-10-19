## 2026-06-19 - Added ARIA labels to web UI icon-only buttons
**Learning:** Found several icon-only buttons (like ⏸, ⏹, ⏪10, 10⏩, 🔉, 🔊, 🔇, and CEC navigation buttons) lacking `aria-label`s, rendering them unreadable to screen readers.
**Action:** Always verify that buttons containing only symbols or emojis have descriptive `aria-label` attributes.

## 2026-06-20 - Redesigned Audio Mixer with animated lines and a11y improvements
**Learning:** Found that static dashed lines in the audio mixer were difficult to read. Also discovered that screen readers couldn't understand the `<svg>` visualization of active routes.
**Action:** Replaced static lines with flowing animated `<path>` elements. Added a `sr-only` class text summary element that accurately reads out all active paths. Ensure `aria-hidden="true"` is applied on purely decorative SVG representations so screen readers do not try to parse complex nodes.
## 2026-07-27 - Accessible aria-labels on dynamic i18n
**Learning:** Do not use static aria-label attributes directly on components with translation inner text if the UI is dynamic, unless specifically using `data-i18n-attr="aria-label"`. This setup preserves inner icon characters (e.g. `×`) while replacing the aria label value through JS mapping `ariaText`.
**Action:** Always combine `data-i18n-attr="aria-label"` alongside `data-i18n="key"` when localizing screen reader text without breaking purely visual icons or shapes inside buttons.
