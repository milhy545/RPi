## 2026-06-19 - Added ARIA labels to web UI icon-only buttons
**Learning:** Found several icon-only buttons (like ⏸, ⏹, ⏪10, 10⏩, 🔉, 🔊, 🔇, and CEC navigation buttons) lacking `aria-label`s, rendering them unreadable to screen readers.
**Action:** Always verify that buttons containing only symbols or emojis have descriptive `aria-label` attributes.

## 2026-06-20 - Redesigned Audio Mixer with animated lines and a11y improvements
**Learning:** Found that static dashed lines in the audio mixer were difficult to read. Also discovered that screen readers couldn't understand the `<svg>` visualization of active routes.
**Action:** Replaced static lines with flowing animated `<path>` elements. Added a `sr-only` class text summary element that accurately reads out all active paths. Ensure `aria-hidden="true"` is applied on purely decorative SVG representations so screen readers do not try to parse complex nodes.

## 2024-11-04 - Dynamic Icon Button Localization & Accessibility
**Learning:** Dynamic icon-only buttons (like tooltips or theme toggles) fail accessibility when injecting raw visual characters without aria-hidden wrappers, and assigning static ARIA labels breaks internationalization (i18n).
**Action:** Always wrap visual characters like emojis or symbols in <span aria-hidden="true"> to hide them from screen readers, and use dynamic i18n properties (dataset.i18nAriaLabel) instead of static aria-label attributes.
