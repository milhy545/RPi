# CSS Token Gap Report (Zpráva o mezerách v CSS tokenech)

## Audit souborů `theme.css` vs `themes.css`
1. **Duplicity a konflikty:**
   - `themes.css` definuje `--bg-primary` (#0d1117), což je identické s `theme.css` `--bg-dark` (#0d1117).
   - `themes.css` definuje `--accent-color` (#58a6ff), což je identické s `theme.css` `--accent-blue`.
   - `themes.css` má další proměnné: `--bg-secondary`, `--bg-tertiary`, `--success-color`, `--success-bg`, `--warning-color`, `--warning-bg`, `--danger-color`, `--danger-bg`, `--info-color`, `--info-bg`. 
   - `theme.css` postrádá varianty pozadí pro stavy success, warning, danger a info.

2. **Plán řešení:**
   - Sloučit všechny barvy z `themes.css` do `theme.css` a standardizovat jmennou konvenci.
   - Aktualizovat `main.css` a všechny ostatní CSS soubory, aby se spoléhaly pouze na tokeny z `theme.css`.
   - Odstranit `themes.css`, protože bude plně nahrazen.

## Audit `responsive.css`
- Nahradí se natvrdo zadané pixelové hodnoty pro rozložení proměnnými `var(--space-*)` a `var(--radius-*)`.

## Audit `audio.css`
- Zajistí se, aby používal `var(--accent-color)`, `var(--bg-card)` atd. místo pevných hex hodnot.

## Audit `main.css`
- Odstraní se jakékoliv hodnoty `#c9d1d9`, `#0d1117`, `#58a6ff` atd. a nahradí se správnými proměnnými `var(--...)`.
