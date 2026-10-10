# Přehled projektu

## Co je tento projekt
`rpi-dashboard` je dashboard pro Raspberry Pi TV s nízkou spotřebou RAM, který slouží jako spouštěč, mediální ovládač, správce zařízení a WebUI řídicí panel.

## Hlavní běžící komponenty
- `tui.py` — hlavní Textual dashboard
- `webserver_8099.py` — WebUI a HTTP/WebSocket řídicí server
- `mode_switcher.py` — spouští a dohlíží na externí aplikace bez narušení stavu dashboardu
- `keys2mpv.py` — daemon pro multimediální klávesy, komunikuje přímo s mpv IPC
- `main.py` — minimální vstupní bod pro testy a kontrolu balíčků

## Systémové rozložení
- **Záložka Player**: Přehrávání YouTube/mpv a diagnostika cookies/věku
- **Záložka Audio**: Výstupy, vstupy, mixer, směrování a DLNA kompenzace
- **Záložka Zařízení**: Párování Bluetooth a správa Wi‑Fi
- **Záložka Kodi**: Legacy JSON-RPC spouštěč pro lokální Kodi instanci
- **Záložka Terminál**: Přístup k terminálu přes WebSocket s podporou tmux

## Reálné příklady použití
- Otevři WebUI a vlož YouTube URL do záložky `Player` pro spuštění přehrávání.
- Použij `Audio` pro přepnutí výchozího výstupu mezi BT, HDMI a DLNA.
- Použij `Zařízení` pro spárování reproduktoru nebo Xbox ovladače, pak se vrať do `Audio` pro směrování.
- Použij záložku `Terminál` pro práci s terminálem bez opuštění TV rozhraní.

## Designová pravidla
- Žádné těžké desktopové prostředí na Pi
- mpv zůstává nejvyšší priorita
- WebUI ovládání musí být bezpečné a intuitivní
- Dokumentace by měla popisovat skutečné chování, ne aspirační
