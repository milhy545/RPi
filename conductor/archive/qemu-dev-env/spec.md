# Specification: QEMU Dev Environment

## Goal
Rozjet RPi OS (Debian/Bookworm ARM) v QEMU na Milhy-PC (x86_64) jako lokální dev/test prostředí pro DumbTV Dashboard. Výsledkem je jednoduchý skript, který spustí emulované RPi a umožní SSH přístup k němu.

## Requirements
1. **Emulace RPi OS v QEMU** — `qemu-system-aarch64` s ARM64 kernelem a rootfs image.
2. **SSH přístup** — z hostu do emulovaného RPi přes port forwarding.
3. **Sdílený adresář** — možnost sdílet kód z hostu do QEMU VM (9p virtio nebo rsync).
4. **Reprodukovatelnost** — setup skript pro jednoduché spuštění (`./qemu-start.sh`).
5. **RAM limit** — QEMU VM emuluje 1 GB RAM (stejně jako reálné RPi).

## Non-Goals
- Grafický výstup (framebuffer/display) — TUI se testuje přes SSH terminál.
- Plná HW emulace (GPIO, Bluetooth, HDMI CEC) — ty se testují až na reálném RPi.
- Kodi — zrušeno, nepotřebujeme.

## Acceptance Criteria
- [ ] `./qemu-start.sh` spustí RPi OS VM bez manuální intervence.
- [ ] SSH z hostu do VM funguje (`ssh -p 2222 pi@localhost` nebo podobně).
- [ ] Uvnitř VM lze spustit `python3` a `pip install textual` (ARM64 binárky).
- [ ] VM má přístup k internetu (pro stahování balíčků).
- [ ] Sdílený adresář mezi hostem a VM funguje.
