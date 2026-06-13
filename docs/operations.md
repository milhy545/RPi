# Operational Playbooks

## QEMU and chroot

### `qemu-start.sh`
Starts the Raspberry Pi OS image in QEMU.

**Example**
```bash
bash qemu-start.sh
```

### `qemu-stop.sh`
Stops the QEMU session.

### `chroot-mount.sh` / `chroot-umount.sh`
Mount and unmount the local rootfs for offline validation.

**Example**
```bash
bash chroot-mount.sh
sudo chroot rootfs /bin/bash
bash chroot-umount.sh
```

## Provisioning

The `provisioning/` scripts are staged install helpers for a fresh Pi setup.

## Common UI workflows

### Play a YouTube video
1. Open `Player`
2. Paste a YouTube URL
3. Click `Play`

### Fix age-restricted playback
1. Open `Player`
2. Click `Cookie status`
3. If needed, run `Age check` with the failing URL
4. Refresh the BrowserOS cookies source if the cookie set is stale

### Pair a Bluetooth speaker
1. Open `Devices`
2. Use `Bluetooth Pairing` scan
3. Pair/connect/trust the device
4. Return to `Audio` and select the output sink

### Connect Wi‑Fi
1. Open `Devices`
2. Scan Wi‑Fi
3. Select or type the SSID
4. Enter the password and connect

### Control media playback by keyboard
- Use the multimedia keys handled by `keys2mpv.py`
- Play/Pause, Next, Previous, Volume +/- and Mute are mapped directly to mpv IPC

## Kodi tab behavior
Kodi is a legacy launcher. Use it only if a local Kodi renderer is intentionally part of the setup.
It sends a URL to `127.0.0.1:9090` using JSON-RPC `Player.Open`.

## Real examples
- Switch HDMI output before starting a TV app.
- Pair a new speaker in Devices, then select it in Audio.
- Check Wi‑Fi status when the TV loses network access.
- Use the Terminal tab for quick shell inspection without leaving the dashboard.
