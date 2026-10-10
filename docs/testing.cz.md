# Testy a ověřování

## Testovací soubory
- `test_testaudio_webui.py` — bezpečné testy WebUI (nemění audio routování)
- `test_audio_mutating_webui.py` — mutující testy (vyžadují `RPIDASHBOARD_MUTATING_AUDIO_TESTS=1`)
- `test_dashboard.py` — testy TUI dashboardu
- `test_production_api.py` — testy produkčního API

## Bezpečné testy
Spouštěj kdykoliv — nemění žádný audio stav:
```bash
python3 -m pytest test_testaudio_webui.py -v
```

## Mutující testy
Pouze když chceš otestovat změnu audio routování:
```bash
RPIDASHBOARD_MUTATING_AUDIO_TESTS=1 python3 -m pytest test_audio_mutating_webui.py -v
```

## Selftest
```bash
curl http://localhost:8099/selftest/testaudio
```

## E2E testy (CDP)
```bash
python3 test_testaudio_webui.py
```

## Pravidla testů
- Testy nikdy nemění audio výchozí routing
- Testy nikdy nepárují/odpojují Bluetooth zařízení
- Testy kontrolují HTTP status kódy a JSON strukturu
- Mutující testy jsou gateované přes env proměnnou
