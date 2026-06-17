# Specification: Bluetooth Audio Loopback (USB Input → BT Soundbar)

## Goal
Route audio from USB sound card input (Alexa AUX) to Bluetooth Soundbar via PipeWire module-loopback.

## Hardware
- **USB Sound Card:** C-Media USB PnP Sound Device (Card 3)
  - Input: `alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.mono-fallback` (mono, 48kHz)
  - Output: `alsa_output.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.analog-stereo`
- **Bluetooth Soundbar:** Samsung Soundbar J-Series (24:4B:03:92:0B:8C)
  - Sink: `bluez_output.24_4B_03_92_0B_8C.1` (stereo, 48kHz)

## Pipeline
```
Alexa → AUX cable → USB Sound Card Input (mono, 48kHz)
    → PipeWire module-loopback (remix mono→stereo, 48kHz, 20ms latency)
    → Bluetooth A2DP Sink (Samsung Soundbar, stereo)
```

## PipeWire Module Configuration
```bash
pactl load-module module-loopback \
  source=alsa_input.usb-C-Media_Electronics_Inc._USB_PnP_Sound_Device-00.mono-fallback \
  sink=bluez_output.24_4B_03_92_0B_8C.1 \
  rate=48000 channels=2 channel_map=front-left,front-right \
  source_dont_move=true sink_dont_move=true \
  latency_msec=20 remix=true
```

## Key Parameters
- **Remix:** `true` — converts mono input to stereo output
- **Latency:** `20ms` — low latency for real-time audio
- **Rate:** `48000` — matches both source and sink
- **Channel Map:** `front-left,front-right` — stereo output
- **Dont Move:** Prevents PipeWire from moving streams

## WebUI Integration
- **Audio Tab:** Loopback status indicator
- **Auto-start:** Systemd service to create loopback on boot
- **Persistence:** Survives USB reconnect (udev rule or systemd restart)

## Acceptance Criteria
- [ ] Alexa playing via AUX → Soundbar outputs audio
- [ ] Volume controlled on Soundbar
- [ ] Loopback survives USB reconnect
- [ ] Loopback survives RPi reboot (systemd)
- [ ] Latency < 50ms (imperceptible)
- [ ] No audio artifacts/crackling