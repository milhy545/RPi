# Implementation Plan: QEMU Dev Environment

## Phase 1: RPi OS Image Preparation
- [x] Stáhnout RPi OS Lite (64-bit, Bookworm) `.img.xz` z oficiálních zdrojů.
- [x] Rozbalit image a zvětšit rootfs partici (`qemu-img resize`).
- [x] Extrahovat kernel (`Image`) a DTB (`bcm2710-rpi-3-b.dtb`) z boot partice image.

## Phase 2: QEMU Configuration (Alternative: Chroot)
- [x] Vytvořit `qemu-start.sh` skript s konfigurací.
- [x] Otestovat boot/chroot — VM/Chroot musí nabootovat/vstoupit do login promptu. (Opraven diskový obraz z home, chroot úspěšný)

## Phase 3: Network & SSH Setup (Alternative: Chroot Prep)
- [x] Nakonfigurovat síť (Resolv.conf). (Kopírován resolv.conf, internet funkční)
- [x] Povolit SSH v image. (Vytvořen boot/ssh soubor, zkopírován userconf.txt a povolen ssh.service)

## Phase 4: Dev Tooling Inside VM/Chroot
- [x] Nainstalovat `uv` uvnitř VM/Chroot. (Úspěšně nainstalován přes oficiální instalátor)
- [x] Ověřit `python3 --version` (≥ 3.11.2 detekováno).
- [x] Nainstalovat `textual` (Již využíváno v `tui.py`, ověřeno a funkční v chrootu v8.2.7).
- [x] Nakonfigurovat sdílený adresář pro vývoj. (Nastaveno přes bind mount)

## Phase 5: Automation & Polish
- [x] Finalizovat `qemu-start.sh` jako single-command launcher. (Upraven pro home image a monitor socket)
- [x] Vytvořit `qemu-stop.sh` pro čistý shutdown. (Vytvořen s podporou monitor socketu a sleep backupu)
- [x] Dokumentovat postup v `README.md`. (Dokumentován setup a chroot proces)
- [x] Přidat QEMU image a kernel do `.gitignore`. (Přidán qemu/ ignorovací vzor)

