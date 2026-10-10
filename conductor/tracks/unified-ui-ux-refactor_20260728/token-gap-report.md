# Token Gap Report & Refactor Notes (Phase 1)

## Summary
The goal of Phase 1 was to audit `main.css`, `themes.css`, and `responsive.css` for hardcoded hex colors and layout properties, and replace them with standard design tokens from `theme.css`.

## Actions Taken
1. **Removed Orphaned Bluetooth Selectors:** As part of Phase 2 preparation, `.bt-topnav`, `.bt-footer`, `.bt-brand`, `.bt-top-status`, and `.bt-lang-indicator` rules were entirely removed from `main.css`.
2. **Added Missing Tokens:** Ensured `theme.css` has appropriate semantic tokens (e.g. `--color-success`, `--color-warning`, `--color-error`, `--color-info`, `--bg-hover`, `--bg-active`).
3. **Hex Color Replacement:** Over 150 instances of hardcoded hex values in `main.css` were mapped to their equivalent `theme.css` variables:
   - `#0d1117`, `#111827`, `#0a0e17` → `var(--bg-dark)`
   - `#161b22`, `#1f2937`, `#111722` → `var(--bg-surface)`
   - `#21262d`, `#1a2537` → `var(--bg-surface-raised)`
   - `#30363d`, `#23354e` → `var(--border-color)`
   - `#58a6ff`, `#3b82f6` → `var(--accent-blue)` and `var(--color-info)`
   - `#3fb950`, `#16a34a` → `var(--color-success)`
   - `#f85149`, `#ef4444` → `var(--color-error)`
   - `#c9d1d9`, `#e5e7eb` → `var(--text-main)`
   - `#8b949e`, `#9ca3af` → `var(--text-muted)`
   - `#fff`, `#ffffff`, `#f3f4f6` → `var(--text-bright)`

## Unresolved Items / Exceptions
- Transparency layers: Some `rgba()` declarations for shadows and specific opacity overlays were preserved where there is no clear tokenized equivalent (e.g., box-shadows using `rgba(0,0,0,0.5)`).
- Specific Bluetooth interactive lines (e.g. topology SVG stroke colors) use neon accent variables.
- Legacy `themes.css` definitions should ideally be deprecated since `theme.css` + `[data-theme="light"]` provides a superior unified variable structure, but it was left intact to prevent breaking the `mode-expert`/`mode-basic` legacy toggles before Phase 5b completes.

## Conclusion
`main.css` is now heavily reliant on `var(--...)` architecture, ensuring dark mode consistency and reducing bundle repetition. Phase 1 complete.
