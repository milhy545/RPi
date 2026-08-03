# Conductor Plan: BT D-Bus Resilience & Multi-Speaker Stability

## 1. Brainstorming & Deep Research (Analýza kořenových příčin)

Na základě rešerše a specifikací RPi projektů jsme identifikovali 4 hlavní problémy ke stabilitě, které vyžadují architektonický zásah:

- **Pády "blueZ D-Bus failed"**: Aktuální backend odesílá synchronní blokující požadavky na `org.bluez` nebo ztrácí referenci na D-Bus proxy objekt ve chvíli, kdy BlueZ daemon na pozadí provede restart. Řešení: asynchronní D-Bus komunikace s automatickým reconnectem.
- **BT Volume Desync (AVRCP ↔ PipeWire)**: Změna hlasitosti na BT reproduktoru se neprojeví v PipeWire a naopak. Řešení: Bidirezionální synchronizace přes `org.bluez.MediaTransport1.Volume`.
- **Odpojování BT reproduktorů v Multi-módu**: Sinky s různými kodeky (A2DP SBC vs AAC) rozbijí časování bufferu. Řešení: Dynamická re-negociace na uzamčený společný formát (SBC 44.1kHz).
- **Topologie adaptérů (USB vs Onboard)**: Uživatel neví, který adaptér obsluhuje které zařízení a jaké jsou limity. Řešení: Vyčítání stromu z `/sys/class/bluetooth/hciX`, varování před přetížením.

## 2. Architektonické kroky (Milestones)

### Fáze 1: Backend — Odolnost D-Busu (Bluetooth Core)

- [ ] Přepsat `rpi_dashboard/services/bluetooth/bluez.py` na asynchronní D-Bus volání.
- [ ] Přidat watcher pro události odpojování (`NameOwnerChanged`) a zapouzdřit všechny D-Bus call metody do `try...except` s exponenciálním backoffem (3 pokusy).
- [ ] Vytvořit custom výjimku `BluetoothDBusError`, která nezboří aplikaci — pouze log + status na frontend.

### Fáze 2: Backend — BT Volume Sync (AVRCP ↔ PipeWire)

- [ ] V `rpi_dashboard/services/audio/mixer.py` upravit `set_sink_volume(sink_id, volume)` — pokud je `sink_id` BT zařízení, volat BlueZ D-Bus `org.bluez.MediaTransport1.Volume` pro sync.
- [ ] V `rpi_dashboard/services/bt.py` upravit BT volume setter — importovat a volat `set_sink_volume` z `rpi_dashboard.services.audio`, aby se PipeWire aktualizoval při AVRCP změně.
- [ ] Přidat unit testy pro bidirezionální sync: `tests/test_services_audio.py`.

### Fáze 3: Backend — Hardware Adapter Profiling

- [ ] Přidat do služby funkci pro skenování HCI adaptérů přes `hciconfig` a `/sys/class/bluetooth/hciX/device/`.
- [ ] Obohatit API o datový model adaptéru: `integrated` (Broadcom/Cypress, `recommended_max_streams=2`) vs `usb` (dle sběrnice).
- [ ] Rozšířit API o telemetrii připojeného BT zařízení: RSSI signál, baterie, aktuální kodek.

### Fáze 4: Backend — Multi-Speaker Engine

- [ ] Vytvořit `rpi_dashboard/services/audio/multi_negotiator.py` — vezme list požadovaných audio výstupů.
- [ ] Před vytvořením combined sink modul proiteruje capabilities jednotlivých BT reproduktorů.
- [ ] Pomocí `pactl`/`wpctl` uzamkne výstupní formát na `s16le 44100Hz` (společný formát).
- [ ] Vytvoří uzamčený spojený sink s pevným bufferováním.

### Fáze 5: Frontend UI a Playwright Testy

- [ ] Implementovat UI pro detailní přehled o BT: RSSI, baterie, driver adaptéru.
- [ ] Upravit dialog multi-audia: zakliknutí jen specifických výstupů, varovný banner (`.adapter-warning`) při překročení limitu adaptéru.
- [ ] Zapsat Playwright E2E testy v `tests/e2e/bt_webui_test.mjs`.

## 3. Akceptační kritéria

- Aplikace nesmí havarovat při manuálním zabití `bluetoothd` v systému (automatické zotavení).
- Přehrávání na HDMI + 1x BT a 2x BT musí běžet nepřerušeně déle než 1 hodinu.
- E2E testy procházejí s úspěšností 100 %.
- `tools/verify-done.sh` prochází s platným CI receipt.

---

## Worker Tasks (Implementační detaily)

### Task 1: D-Bus asynchronní refaktoring
Zanalyzuj `rpi_dashboard/services/bluetooth/bluez.py`. Přepiš hlavní třídu na async přístup (nebo izolované Thready s retry 3 pokusy). Timeout → `BluetoothDBusError` → log + frontend status.

### Task 2: BT Volume Sync
V `mixer.py` přidej kontrolu: je-li sink BT, volat `org.bluez.MediaTransport1.Volume`. V `bt.py` přidej opačný směr: AVRCP změna → `set_sink_volume()` → PipeWire update.

### Task 3: Adapter Capabilities (sysfs)
Nová route v `rpi_dashboard/api/routes.py` — detaily HCI adaptérů přes `hciconfig` + `/sys/class/bluetooth/hciX/device/`. Broadcom/Cypress → `integrated`, jinak `usb`. Přidej RSSI k zařízením.

### Task 4: Multi-Speaker Audio Lock
Nový modul `rpi_dashboard/services/audio/multi_negotiator.py` — vezme seznam sinků, proiteruje capabilities, uzamkne formát na `s16le 44100Hz` přes `pactl`/`wpctl`.

### Task 5: E2E Playwright
Test v `tests/e2e/bt_webui_test.mjs` — simulace přidání Multi-Audio zařízení. Assert: při `integrated` adaptér + 3. BT zařízení → `.adapter-warning` banner. Proklikat všechny DOM elementy.
