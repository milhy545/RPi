# Specifikace tracku: Přístupné ovládání Bluetooth topologie

## Cíl
Doplnit tlačítkům pro přiblížení, oddálení a obnovení Bluetooth topologie srozumitelné české a anglické přístupné názvy.

## Požadavky
- Přístupné názvy se změní při přepnutí jazyka WebUI.
- Stávající ikony, rozložení a akce tlačítek zůstanou stejné.
- Regresní kontrola ověří oba jazyky v prohlížeči.

## Kritéria přijetí
- Tlačítka pro přiblížení, oddálení a obnovení mají správné české a anglické `aria-label`.
- Viditelné znaky `＋`, `−` a `⛶` zůstanou po přepnutí jazyka stejné.
- Cílené kontroly a validační profil `github-safe` projdou.
