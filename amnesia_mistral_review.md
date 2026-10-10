# Vrchní Revizor Report: Amnesia Mistral Implementation Plan

## 1. Obecné Zly

### 1.1. Halucinace Enterprise Architektury
- **Kubernetes/Docker Bias**: Mistral byl z plánování vyřazen z dobrého důvodu. Jeho tendence navrhovat Kubernetes na 1GB RAM Raspberry Pi je nejen směšná, ale přímo nebezpečná. Jakékoliv další zapojení Mistrala by znamenalo kontaminaci plánu zbytečnými abstrakcemi.
- **RabbitMQ**: Navrhovat message broker pro dashboard, který má 3-4 komponenty, je vrchol arogance. To je přesně ten typ "enterprise" overengineeringu, který na 1GB RAM zabije systém.

### 1.2. Paměťová Naivita
- **MatrixRain**: Qwen správně identifikoval, že MatrixRain je paměťový a CPU black hole. Navrhovaná "Option 2: Smazat to" je jediná rozumná cesta. Jakékoliv pokusy o "optimalizaci" jsou ztrátou času — screensaver na Dumb TV je zbytečný luxus.
- **MPV Cache**: Plán sice navrhuje `--demuxer-max-bytes=32MiB`, ale neřeší, co se stane, když uživatel pustí 4K video. Bez hardwarového akceleračního fallbacku (např. `--hwdec=auto`) bude MPV žrát RAM jako hladový pes.
- **Pre-flight RAM Check**: Kontrola `/proc/meminfo` je dobrý nápad, ale plán neřeší, co dělat, když je paměť nedostatečná. Místo odmítnutí spuštění by měl dashboard automaticky přepnout do "low-memory módu" s vypnutými animacemi a omezeným logováním.

### 1.3. Bezpečnostní Díry
- **TOCTOU Race Condition**: Plán sice zmiňuje přesun kontrol `self.state` do lock bloku, ale neřeší, jak zabránit deadlockům při souběžném volání `launch()` a `teardown()`. Bez časového limitu na lock může dojít k trvalému zaseknutí UI.
- **Signal Handlers**: Aktuální návrh `_handle_sigterm` a `_handle_sigint` je nebezpečný. Použití `asyncio.create_task` v signal handleru může vést k neočekávanému chování, pokud se handler zavolá během event loop fáze, která tasky nepodporuje. `loop.call_soon_threadsafe` je lepší, ale stále není ideální — měl by se použít `loop.add_signal_handler`.
- **Cgroup Limity**: Plán navrhuje `MemoryHigh=150M` a `MemoryMax=200M`, ale neřeší, co se stane, když dashboard překročí `MemoryHigh`. Měl by se přidat `MemoryLow` pro postupné škrcení paměti a `OOMScoreAdjust` pro prioritu OOM killeru.

---

## 2. Výkonnostní Bottlenecky

### 2.1. Subprocess Bouře
- **Polling Nastavení**: Volání ~10 forků každých 5 sekund je nepřijatelné. Plán navrhuje TTL cache, ale neřeší, jak cache invalidovat při změnách nastavení. Bez mechanismu pro detekci změn (např. inotify na `/etc`) bude cache zbytečná.
- **sh-c Roura**: Nahrazení `shell=True` za `create_subprocess_exec` je krok správným směrem, ale plán neřeší, jak zabránit shell injection v argumentech. Všechny dynamické argumenty musí být escapovány pomocí `shlex.quote`.

### 2.2. Logování
- **Rotující Logy**: Plán navrhuje `RotatingFileHandler` s limitem 64KB, ale neřeší, kam se budou logy rotovat. Na Raspberry Pi s omezeným úložištěm by měl být použit `TimedRotatingFileHandler` s kompresí starých logů.
- **LogBuffer**: Použití `collections.deque(maxlen=200)` je dobré, ale plán neřeší, jak zabránit ztrátě logů při pádu aplikace. Měl by se přidat mechanismus pro periodické flushování logů na disk.

### 2.3. UI Optimalizace
- **Query_one Cache**: Cacheování `#syslog` elementu je dobrý nápad, ale plán neřeší, jak cache invalidovat při dynamickém přepínání záložek. Bez invalidace bude UI zobrazovat zastaralé informace.
- **Headless Mód**: Plán navrhuje smazání headless módu, ale neřeší, jak dashboard spouštět na systémech bez displeje (např. pro API endpointy). Místo smazání by se měl headless mód refaktorovat na samostatný proces.

---

## 3. Chybějící Kritické Body

### 3.1. Hardwarová Akcelerace
- **MPV**: Plán neřeší hardwarovou akceleraci pro MPV. Bez `--hwdec=auto` bude přehrávání videa žrát CPU a RAM jako divé. Na Raspberry Pi je nutné použít `--hwdec=rpi` nebo `--hwdec=v4l2m2m`.
- **Chromium**: Plán neřeší, jak omezit paměť Chromia. Měly by se přidat argumenty jako `--disable-gpu`, `--single-process`, a `--memory-pressure-off`.

### 3.2. Fallback Mechanismy
- **RAM Fallback**: Plán navrhuje vrátit `0,0` s "N/A" při selhání `/proc/meminfo`, ale neřeší, jak dashboard přizpůsobit nízké paměti. Měl by se přidat fallback mód s vypnutými animacemi a omezeným logováním.
- **Síťové Fallbacky**: Plán neřeší, co dělat při ztrátě síťového připojení. Dashboard by měl mít offline mód s lokálními daty a automatické obnovení připojení.

### 3.3. Testování
- **OOM Testy**: Plán neobsahuje žádné testy pro simulaci OOM podmínek. Měl by se přidat skript, který uměle vyčerpá paměť a ověří, že dashboard nespadne.
- **Race Condition Testy**: Plán neobsahuje testy pro simulaci souběžných requestů na MPV nebo API. Měl by se přidat nástroj jako `wrk` pro zátěžové testování.

---

## 4. Doporučení pro Okamžitou Opravu

1. **Smazat MatrixRain a IdleScreen**: Bez diskuze. Na Dumb TV nemají místo.
2. **Přidat Hardwarovou Akceleraci pro MPV a Chromium**: Bez ní je dashboard nepoužitelný na 1GB RAM.
3. **Refaktorovat Signal Handlers**: Použít `loop.add_signal_handler` a přidat timeouty na všechny locky.
4. **Přidat Cgroup Limity a OOM Prioritu**: Zajistit, aby dashboard neohrozil zbytek systému.
5. **Implementovat Low-Memory Mód**: Automatické přepnutí do úsporného módu při nedostatku paměti.
6. **Přidat Testy pro OOM a Race Conditions**: Zajistit, že dashboard přežije i v extrémních podmínkách.

---

## 5. Závěr

Plán je dobrým základem, ale obsahuje kritické díry, které musí být opraveny před implementací. Bez těchto oprav bude dashboard na 1GB RAM Raspberry Pi nestabilní, nebezpečný a nepoužitelný. Doporučuji okamžitě zahájit opravy podle sekce 4 a následně provést důkladné testování.