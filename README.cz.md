# Raspberry Pi Dumb TV & Multimediální Centrum

[![Platform: Raspberry Pi OS](https://img.shields.io/badge/Platform-Raspberry%20Pi%203%20Model%20B-red.svg)](https://www.raspberrypi.com/)
[![Kernel: Linux](https://img.shields.io/badge/Kernel-Linux%20Affinity%20Tuning-orange.svg)](https://www.kernel.org/)
[![UI: Textual TUI](https://img.shields.io/badge/UI-Textual%20TUI-blue.svg)](https://github.com/Textualize/textual)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)  
[🇬🇧 English version available here](./README.md)

Nízkonákladové multimediální centrum a dashboard pro obývací televizi postavené na Raspberry Pi 3 Model B, vyladěné na absolutní hranici možností čipu pomocí **přísné CPU afinity jader a izolace hardwarových přerušení (IRQ)**.

Umožňuje plynulé přepínání mezi terminálovým Textual dashboardem, celoobrazovkovým přehráváním 1080p videa přes MPV a streamováním her přes Steam Link z hlavního počítače.

---

## 🔬 Inženýrská studie: Překonání fyzických limitů křemíku

Tento projekt sloužil jako reálná výzkumná laboratoř pro pochopení chování Linuxového jádra na slabém 4jádrovém ARM SoC (Broadcom BCM2837, 1GB RAM).

### 1. Termální saturace: Core Packing vs. Core Spreading
- **Problém:** Standardní CFS plánovač Linuxu rovnoměrně rozhazuje zátěž na všechna 4 jádra (Core Spreading). Všechna jádra tak zůstávají neustále aktivní a nemohou přejít do úsporných stavů (C-states). Masivní únikový proud (static leakage) rychle přehřál SoC nad 80–85 °C, což spustilo tvrdý termální throttling na **600 MHz**, kde hardwarové dekódování videa (`v4l2m2m-copy`) v MPV okamžitě zkolabovalo.
- **Řešení (Core Packing):** Přísné uzamčení video zátěže na **jádra 1 a 2** (`taskset -c 1,2`). Tím se maximalizují zásahy v L1 cache, eliminuje se zahlcení sdílené 512 KiB L2 cache a zbylá jádra mohou šetřit teplo.

### 2. Koexistence Wi-Fi a Bluetooth (Hardwarový limit čipu Cypress)
- Na Raspberry Pi 3 sdílí Wi-Fi a Bluetooth stejný fyzický čip a jedinou 2.4 GHz anténu. Časový multiplex způsoboval zasekávání zvuku kdykoliv probíhal síťový přenos.
- V MPV slouží zvuk jako hlavní referenční vztažný bod (`video-sync=audio`). Jakýkoliv výpadek zvuku v PipeWire okamžitě způsobil masivní zahazování snímků videa.

### 3. Matice alokace 4 CPU jader

| Jádro | Alokace a Úloha | Inženýrské zdůvodnění |
| :--- | :--- | :--- |
| **Core 0** | **Úklid & IRQ Štít** | Zpracovává veškerá hardwarová přerušení (USB, Wi-Fi, Ethernet, SD karta) a procesy na pozadí (`NetworkManager`, `tailscaled`, `Textual TUI`). |
| **Cores 1 & 2** | **Video Engine** | Hlavní vlákno MPV a `v4l2m2m-copy` dekodér uzamčené přes `taskset -c 1,2`. |
| **Core 3** | **Real-Time Zvuk & Záchranná rezerva** | Rezervováno pro PipeWire / WirePlumber s garantovanou prioritou reálného času (`rtprio 95` přes `/etc/security/limits.d/25-pw-rlimits.conf`, bez nestabilního RTKitu). Jádro 3 spí v úsporném režimu a pomáhá jádrům 1 a 2 pouze při extrémních špičkách (>160 % zátěže po dobu >3s). |

---

## 🛠️ Struktura projektu a odkazy na existující dokumentaci

- `main.py` — Vstupní bod aplikace
- `tui.py` — Textual TUI dashboard
- `webserver.py` — WebUI, REST API a WebSocket server (port 8099)
- `mode_switcher.py` — Správce popředí a přepínání aplikací
- `keys2mpv.py` — Ovladač multimediálních kláves pro MPV
- [Index dokumentace](./docs/README.md)
- [Přehled projektu](./docs/overview.md)
- [WebUI a API reference](./docs/webserver-8099.md)
- [Reference Textual dashboardu](./docs/tui.md)
- [Reference přepínače režimů](./docs/mode-switcher.md)
- [Démon multimediálních kláves](./docs/keys2mpv.md)
- [Průvodce testováním a verifikací](./docs/testing.md)
- [Operační postupy](./docs/operations.md)
