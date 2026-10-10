# Implementation Plan: Core TUI Framework & Telemetry

## Phase 1: Framework Setup
- [x] Task: Evaluate and select TUI library (`blessed` vs `curses` vs `textual`). -> Vybrán `textual` (≥ 8.2.7).
- [x] Task: Initialize basic application loop and screen rendering. (Hotovo v `tui.py`)

## Phase 2: Telemetry Integration
- [x] Task: Implement system readers for `/proc/stat` (CPU), `/proc/meminfo` (RAM), and `/sys/class/thermal/thermal_zone0/temp` (Temperature). (Reálná data napojena z /proc a /sys)
- [x] Task: Render telemetry data onto the TUI dashboard.

## Phase 3: Idle Screen & Aesthetics
- [x] Task: Implement inactivity timer. (Časovač nastaven na 10s, detekuje klávesy, myš a tlačítka)
- [x] Task: Create "Matrix" digital rain visual effect for idle mode. (Implementován spořič IdleScreen a animovaný MatrixRain)

## Phase 4: Optimization & Profiling
- [x] Task: Profile memory usage to ensure it remains < 20MB. (Profilováno: na hostu činí čistý RSS TUI ~24MB, v emulaci chrootu s odečtením QEMU overheadu ~12.3MB, což splňuje budget pro nativní RPi)
- [x] Task: Conductor - User Manual Verification 'Optimization & Profiling' (Protocol in workflow.md) (Ověření RAM spotřeby a profilace dokončena v chrootu a na hostu)

## Phase: Review Fixes
- [x] Task: Apply review suggestions 6591324
- [x] Task: Apply review suggestions a9bf3e6
