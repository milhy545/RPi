### What:
Added explicit programmatic associations (`for` attributes) to all standalone `<label>` elements linking them to their respective inputs (`<input>`, `<select>`, `<textarea>`). Also added `aria-label`s to interactive inputs that lacked accessible names (e.g., YouTube URL inputs, sliders, Wi-Fi configuration).

### Why:
Inputs without explicit labels or accessible names are extremely difficult for screen-reader users to interact with. A common pattern in older vanilla HTML is relying on visual proximity instead of semantic linkage. Adding explicit linkages not only exposes the context programmatically to assistive technologies, but it also increases the clickable hit area for inputs with visible labels (clicking the label focuses the input).

### Before/After:
Before, inputs had labels visually next to them, but screen readers couldn't associate them. Inputs like `YouTube URL` were completely unlabeled. Now, clicking the text "Role:" correctly focuses the Role dropdown.

### Accessibility:
Significantly improved accessibility by providing accessible names to numerous form elements and increasing interactive hit areas for standard input fields.
