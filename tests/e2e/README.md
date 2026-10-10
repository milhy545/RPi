# RPi-TV WebUI E2E Tests

Tato složka obsahuje end-to-end testy pro WebUI RPi Dashboardu, napsané pomocí [Playwrightu](https://playwright.dev/).

Z důvodu omezených hardwarových prostředků (RAM) na Raspberry Pi by se tyto testy **nikdy neměly spouštět přímo na RPi**. Místo toho je spouštějte ze silnějšího stroje (např. vývojářského PC), který má síťový přístup k RPi.

## Požadavky

* Node.js (v18+)
* NPM nebo Yarn

## Nastavení a spuštění

1. Zkopírujte nebo stáhněte složku na váš vývojářský stroj.
2. Nainstalujte závislosti:
   ```bash
   npm install
   npx playwright install chromium
   ```
3. Spusťte testy a nasměrujte je na IP adresu vašeho RPi (nahraďte `192.168.0.205` za skutečnou IP adresu):
   ```bash
   TARGET_URL=http://192.168.0.205:8080 npm test
   ```

## Co testy pokrývají
* WebUI se načte a v konzoli prohlížeče nejsou errory.
* **Video Playback**: Spuštění YouTube videa (`/mpv/play`), ověření načtení titulku, kontroly běžícího přehrávání (`pos` a `dur`) a bezpečné zastavení.
* **PWA Share Intent**: Schopnost přijmout URL přes sdílení na Androidu (parametr `?share_url=`).
* Tlačítka módů (Steam, Spotify, mpv).
* PWA manifest a navigaci po kartách.

Všechny výsledné screenshoty se vygenerují do složky `artifacts/`.
