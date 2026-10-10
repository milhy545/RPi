# Implementation Plan - Bluetooth Gamepad & Stuttering Fix

## Goal
Opravit sekání zvuku (stuttering) u Bluetooth soundbaru a zprovoznit párování Xbox ovladače.

Description: Stále mi jede spárovat Xbox ovladač a celkově si nejsem jistý jestli vůbec k něčemu se spárovat jde kromě toho soundbaru a když na něj přepnu tak v pravidelných intervalech asi 30 vteřin nebo kolika se zašli zvuk sekat pak to za chvíli jde a pak zase je to celkem pravidelně

## Tasks
| # | Description | Owner | Status |
|---|-------------|-------|--------|
| 1 | **BT Audio Stutter:** Diagnostika PipeWire buffer/latency hodnot. Možná kolize Wi-Fi s Bluetooth na RPi anténě. Vynutit vyšší buffer nebo změnit profil (A2DP). | agent | ⏳ Pending |
| 2 | **Xbox Controller Pairing:** Nainstalovat a povolit `xpadneo` (ovladač pro Xbox One S/Series BT) nebo aplikovat `bluetoothctl` ERTM fix, který standardně blokuje Xbox Gamepady na Linuxu. | agent | ⏳ Pending |
| 3 | **Testování:** Spárovat ovladač a nechat 5 minut hrát hudbu přes BT soundbar bez záseků. | agent | ⏳ Pending |
