## 2026-07-27 - Better Accessibility For RPi-TV

**Learning:** We need to make sure buttons with only symbols (like closing Modals) have explicit `aria-label`s, that ALL input elements and select drop downs have explicitly associated `<label>` or visually hidden labels. This dramatically helps with keyboard navigation and screen readers! Also some `for` attributes on existing labels were missing their association ID link to the input element!

**Action:** When working on UI code in the project, ensure that labels explicitly use `for` matching the target ID and if labels aren't desired visually we can add `<label for="..." style="display:none">`. Added `aria-label` to some `x` close modal buttons and bluetooth panel overview buttons.

## 2026-07-27 - Proper Accessibility For RPi-TV

**Learning:** When making form inputs accessible, adding a `<label>` with `display: none` is an accessibility anti-pattern because elements with `display: none` are removed from the accessibility tree, meaning screen readers will ignore them entirely. The correct approach for a visually hidden label is to apply an `aria-label="..."` attribute directly to the `<input>` element. Also, be careful when adding static `aria-label`s to buttons that use dynamic translatable text (e.g., `data-bt-i18n-cs`), as the static `aria-label` will override the inner text for screen readers, breaking internationalization.

**Action:** When working on UI code in the project, ensure that labels explicitly use `for` matching the target ID. For inputs without visible labels, apply an `aria-label` directly on the input. Avoid hardcoding English `aria-label`s on elements that require translation.
