# Implementation Plan - mpv Auto-Return on EOF

## Goal
Ukončit přehrávání a vrátit se do dashboardu, když video skončí, místo ponechání černé obrazovky (kvůli předchozí fixaci `--keep-open=always`).

Description: Nastavit aby se přehrávač po dokončení přehrávání to znamená přehrání filmu až na konec tak aby nezůstala ta černá obrazovka tam tak ať se vrací zpátky do dashboardu po dokončení přehrávání

## Tasks
| # | Description | Owner | Status |
|---|-------------|-------|--------|
| 1 | **IPC Event Listener:** V `webserver.py` nebo `mode_switcher.py` poslouchat na mpv eventy typu `eof-reached` nebo konec playlistu. | agent | ⏳ Pending |
| 2 | **Clean Shutdown Trigger:** Jakmile event přijde, poslat korektní `quit` příkaz do mpv a uvolnit TUI. | agent | ⏳ Pending |
| 3 | **Testování:** Ověřit, že to nerozbije socket jako v minulosti (zabezpečit plynulé obnovení TUI bez freeze). | agent | ⏳ Pending |
