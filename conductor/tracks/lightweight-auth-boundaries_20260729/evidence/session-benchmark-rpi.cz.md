# Session Validation Benchmark — Live RPi Evidence (CZ)

**Host:** rpi-tv  
**Python:** 3.11.2  
**Datum:** 2026-07-30T13:49:11+01:00  
**Testovaný soubor:** `rpi_dashboard/auth.py`  
**SHA256 souboru:** `c6ac15a48e6b5ef90b7c6c97116b946cbfe9ee902673cec0e5065c6b05942d5a`  
**Benchmark:** vlastní Python skript s 1000 přímými voláními `SessionStore.validate()`

## Výsledky

| Metrika | Naměřeno | Limit | Stav |
|---------|----------|-------|------|
| Median  | 0.0368 ms | ≤ 1 ms | PASS |
| P95     | 0.0452 ms | ≤ 5 ms | PASS |
| Max     | 0.2599 ms | —     | —   |

## Provenience

Soubor `auth.py` byl testován v **izolovaném dočasném balíčku** (zkopírován do
samostatného adresáře obsahujícího pouze `rpi_dashboard/__init__.py` a
zkopírovaný `auth.py`). Produkční runtime na rpi-tv — včetně běžícího
dashboards, `auth.json` a stavu služeb — nebyl během testu **nijak
modifikován, čten ani zpřístupněn**.

### Poznámka k testovacímu harnessi

První pokus s holým `importlib` harnessem selhal s chybou
`AttributeError: 'NoneType' object has no attribute '__dict__'` během
zpracování dataclass, protože dynamicky nahraný modul nebyl vložen do
`sys.modules`. Benchmark byl úspěšně opakován s korektním package-import
přístupem (dočasný adresář s `rpi_dashboard/__init__.py` a zkopírovaným
`auth.py`), který modul umístil do `sys.modules` a produkoval výše uvedené
výsledky.

## Závěr

Všechny naměřené hodnoty jsou výrazně pod specifikovanými limity (median ≤ 1 ms,
p95 ≤ 5 ms). Session validation na cílovém RPi neprovádí žádný PBKDF ani
I/O operace — pouze SHA-256 hash a vyhledávání v dictionary pod zámkem.
Implementace Phase 3 `SessionStore` je validována na cílovém hardwaru.
