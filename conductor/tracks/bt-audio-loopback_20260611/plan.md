# Implementation Plan: Bluetooth Audio Loopback

## Phase 1: Pair Bluetooth Soundbar
- [x] Task: `bluetoothctl` pair/connect Samsung Soundbar (24:4B:03:92:0B:8C)
- [x] Task: Verify A2DP sink appears in `pactl list short sinks`

## Phase 2: Create Loopback
- [x] Task: Identify correct source/sink names
  - Source: `alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.mono-fallback`
  - Sink: `bluez_output.24_4B_03_92_0B_8C.1`
- [x] Task: Create loopback with correct parameters
  - `pactl load-module module-loopback ... remix=true`

## Phase 3: Optimize
- [x] Task: Set BT sink volume to 100% (`pactl set-sink-volume ... 100%`)
- [x] Task: Disable USB autosuspend (`echo on > /sys/bus/usb/devices/*/power/control`)
- [x] Task: Tune latency (20ms) and remix settings

## Phase 4: Persistence
- [ ] Task: Create systemd service for auto-start on boot
- [ ] Task: Add udev rule to recreate loopback on USB reconnect

## Phase 4: Validation
- [x] Test: Alexa playing via AUX → Soundbar outputs audio
- [x] Test: Volume control on Soundbar works
- [ ] Conductor - User Manual Verification 'bt-audio-loopback'