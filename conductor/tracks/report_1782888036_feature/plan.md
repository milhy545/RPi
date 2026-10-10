# Implementation Plan - Audio Matrix/Graph UI

## Goal
Vylepšit WebUI audio mixer z jednoduchého 1-vstup -> 1-výstup (default sink) na komplexní patchbay (matice nebo grafické propojování čarami).

Description: Vylepšit audio mixér tak aby šlo volně naftavovat vstupy i výstupy buď hromadně To znamená že třeba ze dvou vstupů do několika výstupů současně a nebo i odděleně To znamená že jeden vstup na jeden výstup bez ovlivnění ostatního a tak po různě prostě doplnit více volnosti do audio mixéru a propojit ho s tou Grafikou že by se třeba jenom označovali vstupy výstupy A nebo by se ručně natáhla, mezi zařízeními které bych chtěl propojit

## Tasks
| # | Description | Owner | Status |
|---|-------------|-------|--------|
| 1 | **Backend API (PipeWire/pw-link):** Vytvořit API endpointy pro mapování (pw-link) specifických uzlů bez ohledu na default sink. | agent | ✅ Done |
| 2 | **WebUI (Frontend):** Vytvořit drag-and-drop rozhraní s HTML5 Canvas nebo SVG pro vizualizaci audio uzlů (jako Helvum). | agent | ✅ Done (Matrix UI) |
| 3 | **State Management:** Udržování stavu propojení při odpojení/připojení USB a Bluetooth. | agent | ✅ Done |
