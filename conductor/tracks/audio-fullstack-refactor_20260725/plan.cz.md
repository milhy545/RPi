## Kontext
Track `audio-fullstack-refactor_20260725` modularizuje audio backend, přidává globální hlasitost a WebUI topologii a zároveň sleduje obousměrnou synchronizaci PipeWire/AVRCP a modernizaci TUI. Podrobný technický checklist je udržován v [anglickém plánu](./plan.md); tento dokument je jeho český stavový protějšek.

## Aktuální stav implementace (audit 2026-08-02)
- [x] Modulární balíček `rpi_dashboard/services/audio/` nahradil původní monolit a zachovává veřejné importy.
- [x] Služba a API globální hlasitosti, WebUI slider a plátno topologie jsou implementované a automatizovaně testované.
- [ ] Hlasitost PipeWire sinku a BlueZ AVRCP je synchronizovaná v obou směrech.
- [ ] Textual TUI obsahuje plánovaný `AudioFlowDiagram` a rozložení globální hlasitosti.
- [ ] Jsou zaznamenané cílené AVRCP/TUI testy a ověření na cílovém RPi.

Tento stavový blok je autoritativní pro zbývající rozsah. Otevřené úkoly níže odpovídají fázím anglického plánu.

## Fáze 1: Modularizace backendu
- [x] Původní `audio.py` je nahrazený balíčkem modulů pro stav, mixer, matici, multi-output, keepalive, profily a latenci.
- [x] Veřejné importy zůstávají zpětně kompatibilní.

## Fáze 2: BT volume sync a globální hlasitost
- [ ] Doplnit AVRCP zápis při změně hlasitosti Bluetooth sinku.
- [ ] Propagovat změny AVRCP zpět do PipeWire.
- [x] Implementovat globální hlasitost a endpoint `/audio/volume/global`.

## Fáze 3: WebUI topologie
- [x] Implementovat slider globální hlasitosti a dynamickou audio topologii.
- [ ] Synchronizovat slider hlasitosti mezi Audio a Bluetooth tabem v obou směrech.

## Fáze 4: Modernizace TUI
- [ ] Přidat `AudioFlowDiagram`, seznam sinků a slider globální hlasitosti.
- [ ] Zachovat české TUI řetězce bez diakritiky kvůli TV konzoli.

## Fáze 5: Testy
- [x] Pokrýt globální hlasitost jednotkovými testy.
- [ ] Doplnit mock test obousměrného AVRCP/PipeWire propojení.
- [ ] Doplnit cílené testy nového audio TUI.

## Fáze 6: Ověřovací brána
- [ ] Spustit kompletní pytest, lint a `tools/verify-done.sh` po dokončení AVRCP a TUI částí.
- [ ] Ověřit audio chování na cílovém RPi s reálným Bluetooth zařízením.

## Kritéria přijetí
- [x] Modulární audio balíček a globální master API jsou nasazené.
- [x] WebUI zobrazuje topologii a ovládá globální hlasitost.
- [ ] AVRCP a PipeWire hlasitost jsou obousměrně synchronizované.
- [ ] TUI zobrazuje ASCII tok audia.
- [ ] Kompletní CI a cílové hardwarové ověření jsou doložené.
