# CSS Token Gap Report

## Audit of `theme.css` vs `themes.css`
1. **Duplicates and Conflicts:**
   - `themes.css` defines `--bg-primary` (#0d1117), which is identical to `theme.css` `--bg-dark` (#0d1117).
   - `themes.css` defines `--accent-color` (#58a6ff), identical to `theme.css` `--accent-blue`.
   - `themes.css` has additional variables: `--bg-secondary`, `--bg-tertiary`, `--success-color`, `--success-bg`, `--warning-color`, `--warning-bg`, `--danger-color`, `--danger-bg`, `--info-color`, `--info-bg`. 
   - `theme.css` lacks background variants for success, warning, danger, and info.

2. **Resolution Plan:**
   - Merge all colors from `themes.css` into `theme.css` and standardize the naming convention (e.g. `--bg-primary` instead of `--bg-dark`, `--bg-card`, etc., or map them correctly).
   - Update `main.css` and all other CSS files to only rely on `theme.css` tokens.
   - Remove `themes.css` if it's completely superseded.

## Audit of `responsive.css`
- Will replace hardcoded pixel values for layouts with `var(--space-*)` and `var(--radius-*)` where applicable.

## Audit of `audio.css`
- Will ensure it uses `var(--accent-color)`, `var(--bg-card)`, etc. instead of hardcoded hex values.

## Audit of `main.css`
- Will strip out any `#c9d1d9`, `#0d1117`, `#58a6ff`, etc., and replace them with correct `var(--...)`.
