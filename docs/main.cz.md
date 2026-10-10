# Hlavní vstupní bod

## Popis
`main.py` je minimální vstupní bod používaný pro testy a kontrolu balíčků.

## Funkce
- Importuje a spouští Textual dashboard z `tui.py`
- Slouží jako entry point pro `pyproject.toml`
- Neprovádí žádnou business logiku — jen spouští dashboard

## Použití
```bash
python3 main.py
```

## Poznámky
- Pro běžné použití spouštěj přes `python3 main.py`
- WebUI se spouští samostatně přes `python3 webserver_8099.py`
