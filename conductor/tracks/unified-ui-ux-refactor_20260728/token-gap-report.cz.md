# Zpráva o chybějících tokenech a poznámky k refaktoringu (Fáze 1)

## Shrnutí
Cílem Fáze 1 bylo provést audit `main.css`, `themes.css` a `responsive.css` na pevně zadané hexadecimální barvy a vlastnosti rozložení a nahradit je standardními designovými tokeny z `theme.css`.

## Provedené kroky
1. **Odstraněny nepoužívané Bluetooth selektory:** V rámci přípravy na Fázi 2 byly z `main.css` zcela odstraněny pravidla `.bt-topnav`, `.bt-footer`, `.bt-brand`, `.bt-top-status` a `.bt-lang-indicator`.
2. **Přidány chybějící tokeny:** Bylo zajištěno, že `theme.css` obsahuje vhodné sémantické tokeny (např. `--color-success`, `--color-warning`, `--color-error`, `--color-info`, `--bg-hover`, `--bg-active`).
3. **Nahrazení hexadecimálních barev:** Přes 150 výskytů pevně zadaných hex hodnot v `main.css` bylo namapováno na jejich ekvivalentní proměnné v `theme.css`:
   - `#0d1117`, `#111827`, `#0a0e17` → `var(--bg-dark)`
   - `#161b22`, `#1f2937`, `#111722` → `var(--bg-surface)`
   - `#21262d`, `#1a2537` → `var(--bg-surface-raised)`
   - `#30363d`, `#23354e` → `var(--border-color)`
   - `#58a6ff`, `#3b82f6` → `var(--accent-blue)` a `var(--color-info)`
   - `#3fb950`, `#16a34a` → `var(--color-success)`
   - `#f85149`, `#ef4444` → `var(--color-error)`
   - `#c9d1d9`, `#e5e7eb` → `var(--text-main)`
   - `#8b949e`, `#9ca3af` → `var(--text-muted)`
   - `#fff`, `#ffffff`, `#f3f4f6` → `var(--text-bright)`

## Nevyřešené položky / Výjimky
- Vrstvy průhlednosti: Některé deklarace `rgba()` pro stíny a specifická překrytí neprůhlednosti byly zachovány tam, kde není jasný ekvivalent v tokenech (např. box-shadows používající `rgba(0,0,0,0.5)`).
- Specifické interaktivní Bluetooth prvky (např. barvy tahů v SVG topologii) používají neonové akcentní proměnné.
- Starší definice v `themes.css` by ideálně měly být zavrženy, protože `theme.css` + `[data-theme="light"]` poskytuje lepší jednotnou strukturu proměnných, ale byly ponechány nedotčeny, aby nedošlo k rozbití přepínačů `mode-expert`/`mode-basic` před dokončením Fáze 5b.

## Závěr
`main.css` nyní silně spoléhá na architekturu `var(--...)`, což zajišťuje konzistenci tmavého režimu a snižuje opakování v kódu. Fáze 1 je dokončena.
