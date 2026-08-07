# Conductor Plan: BT D-Bus Resilience & Multi-Speaker Stability

## 1. Brainstorming & Deep Research (Analýza kořenových příčin)

Na základě rešerše a specifikací RPi projektů jsme identifikovali 4 hlavní problémy ke stabilitě, které vyžadují architektonický zásah:

- **Pády "blueZ D-Bus failed"**: Aktuální backend odesílá synchronní blokující požadavky na `org.bluez` nebo ztrácí referenci na D-Bus proxy objekt ve chvíli, kdy BlueZ daemon na pozadí provede restart. Řešení: asynchronní D-Bus komunikace s automatickým reconnectem.
- **BT Volume Desync (AVRCP ↔ PipeWire)**: Změna hlasitosti na BT reproduktoru se neprojeví v PipeWire a naopak. Řešení: Bidirezionální synchronizace přes `org.bluez.MediaTransport1.Volume`.
- **Odpojování BT reproduktorů v Multi-módu**: Sinky s různými kodeky (A2DP SBC vs AAC) rozbijí časování bufferu. Řešení: Dynamická re-negociace na uzamčený společný formát (SBC 44.1kHz).
- **Topologie adaptérů (USB vs Onboard)**: Uživatel neví, který adaptér obsluhuje které zařízení a jaké jsou limity. Řešení: Vyčítání stromu z `/sys/class/bluetooth/hciX`, varování před přetížením.

## 2. Architektonické kroky (Milestones)

### Fáze 1: Backend — Odolnost D-Busu (Bluetooth Core)

- [x] Přepsat `rpi_dashboard/services/bluetooth/bluez.py` na asynchronní D-Bus volání.
- [x] Přidat watcher pro události odpojování (`NameOwnerChanged`) a zapouzdřit všechny D-Bus call metody do `try...except` s exponenciálním backoffem (3 pokusy).
- [x] Vytvořit custom výjimku `BluetoothDBusError`, která nezboří aplikaci — pouze log + status na frontend.

### Fáze 2: Backend — BT Volume Sync (AVRCP ↔ PipeWire)

- [x] V `rpi_dashboard/services/audio/mixer.py` upravit `set_sink_volume(sink_id, volume)` — pokud je `sink_id` BT zařízení, volat BlueZ D-Bus `org.bluez.MediaTransport1.Volume` pro sync.
- [x] V `rpi_dashboard/services/bt.py` upravit BT volume setter — importovat a volat `set_sink_volume` z `rpi_dashboard.services.audio`, aby se PipeWire aktualizoval při AVRCP změně.
- [x] Přidat unit testy pro bidirezionální sync: `tests/test_services_audio.py`.

### Fáze 3: Backend — Hardware Adapter Profiling

- [x] Přidat do služby funkci pro skenování HCI adaptérů přes `hciconfig` a `/sys/class/bluetooth/hciX/device/`.
- [x] Obohatit API o datový model adaptéru: `integrated` (Broadcom/Cypress, `recommended_max_streams=2`) vs `usb` (dle sběrnice).
- [x] Rozšířit API o telemetrii připojeného BT zařízení: RSSI signál, baterie, aktuální kodek.

### Fáze 4: Backend — Multi-Speaker Engine

- [x] Vytvořit `rpi_dashboard/services/audio/multi_negotiator.py` — vezme list požadovaných audio výstupů.
- [x] Před vytvořením combined sink modul proiteruje capabilities jednotlivých BT reproduktorů.
- [x] Pomocí `pactl`/`wpctl` uzamkne výstupní formát na `s16le 44100Hz` (společný formát).
- [x] Vytvoří uzamčený spojený sink s pevným bufferováním.

### Fáze 5: Real-Status WebUI and BT Audio Diagnostics

- [x] Inventory every WebUI status pill, badge, summary, quick-action state, and footer value. Remove decorative operational claims and map each retained state to a documented live API field, collection timestamp, and explicit loading/stale/degraded/unavailable behaviour.
- [x] Replace the hard-coded footer claims (`Service Running`, `Bluetooth Ready`, `Audio HDMI`) with bounded periodic status aggregation. Do not require the user to open the hardware panel before CPU/RAM/temperature values become truthful.
- [x] Collect real RPi samples first (`wpctl status`, `pactl list short sinks`, default sink, active stream links, and relevant WirePlumber metadata), document parser provenance, and prove parsing in a scratch script before production implementation.
- [x] Replace the fixed `bt_soundbar`/`alexa_to_bt` readiness assumption with dynamic matching between connected BlueZ audio devices and PipeWire/WirePlumber sinks/routes. Treat a default BT sink, an active stream routed to the BT sink, or an explicitly enabled loopback according to their real semantics; an optional inactive loopback alone is not a blocker.
- [x] Represent `pass`, `blocked`, `not applicable`, `unknown`, and `stale` separately. No connected BT audio device must produce `not applicable`, while command/API failure must produce `unknown` or `degraded`, never a fabricated red or green result.
- [x] Implement UI for detailed BT information: RSSI, battery, codec, adapter driver, and actionable reason text for every non-passing readiness state.
- [x] Update the multi-audio dialog to select explicit outputs and show `.adapter-warning` when adapter limits are exceeded.

### Fáze 6: Tests and Live Validation

- [x] Add focused backend tests for dynamic sink identity, default route, active stream, optional loopback, multiple BT sinks, no connected BT audio device, stale evidence, bounded command timeout, and malformed real command output.
- [x] Add static regression tests forbidding hard-coded operational success labels/classes in production WebUI markup and payloads.
- [x] Extend `tests/e2e/bt_webui_test.mjs` with loading, real-success, blocked, not-applicable, stale, and backend-unavailable states, plus the integrated-adapter third-device warning.
- [x] Run Playwright from Milhy-PC against the exact staged RPi candidate. Verify the two reported readiness rows become green only when supported by live audio evidence and preserve screenshots/API evidence for both connected and disconnected cases.
- [x] Run the one-hour HDMI + one-BT and two-BT stability checks without disrupting user playback, then complete exact-SHA RPi validation and receipt generation.

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

### Task 5: Truthful WebUI Status and Dynamic Audio Readiness
Audit the bottom status line and all status-like WebUI components. Replace hard-coded success labels with backend-derived state plus freshness/error semantics. Refactor BT soundbar readiness to correlate actual BlueZ audio devices with real PipeWire/WirePlumber sinks and routes instead of assuming `bt_soundbar` and `alexa_to_bt`. Keep optional loopback state distinct from valid direct BT routing.

### Task 6: Backend and Playwright Evidence
Add deterministic backend tests from documented real command samples and fuzzed identifiers. Extend `tests/e2e/bt_webui_test.mjs` to cover truthful loading/pass/blocked/not-applicable/stale/unavailable rendering, the two reported audio readiness rows, and the integrated-adapter third-device warning. Run browser tests remotely from Milhy-PC against an exact-SHA staged RPi candidate; never run a browser on RPi.
