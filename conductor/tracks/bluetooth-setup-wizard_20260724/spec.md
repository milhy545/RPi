# Bluetooth Setup Wizard

## Problem statement
The RPi 3 internal Bluetooth (`hci0`) cannot handle multiple high-bandwidth A2DP streams simultaneously due to UART bus limits and shared Wi-Fi antenna. Connecting multiple speakers (Multi-Output) requires load-balancing audio to a USB dongle (`hci1`) and keeping IO/phones on `hci0`. Setting this up manually via CLI is cumbersome.

## Desired outcome
A guided, 5-step interactive wizard in the Web UI that resets all Bluetooth state, automatically assigns the best adapters for audio vs. IO, and guides the user through re-pairing their devices to the correct adapters. Additionally, the default Bluetooth tab view should be changed from "Advanced" to "Basic" to avoid overwhelming users.

## Scope and requirements
1. **Default View**: Change the initial Bluetooth tab view to "Basic" (hide advanced technical metrics by default).
2. **Wizard Step 1 (Reset)**: Warn the user and execute a complete unpair of all devices across all adapters, resetting BT state.
3. **Wizard Step 2 (Adapter Selection)**: Automatically detect and propose the USB adapter (if present) for Audio Streams, and the integrated adapter for IO/Controllers. Allow user override.
4. **Wizard Step 3 (IO Pairing)**: Put the IO adapter into pairing mode. Guide the user to pair gamepads, keyboards, etc.
5. **Wizard Step 4 (Audio Pairing)**: Put the Audio adapter into pairing mode. Guide the user to pair speakers. If a mobile phone is detected, ask whether it acts as an audio source (streaming to RPi) or sink.
6. **Wizard Step 5 (Summary)**: Display the overall topology diagram (same format as BT Settings) for review. Provide Confirm or Back options.

## Out of scope
- Implementation of new Bluetooth profiles (e.g., BLE MIDI, HID proxy).
- Purchasing or hardware installation instructions for USB dongles.

## Acceptance criteria
- [ ] Bluetooth tab opens in "Basic" view by default.
- [ ] Wizard can be launched from the UI.
- [ ] Step 1 successfully unpairs all existing devices.
- [ ] Step 2 correctly defaults to USB for audio and integrated for IO when both are present.
- [ ] Step 3 and 4 successfully pair devices strictly to their assigned adapters.
- [ ] Step 5 displays the correct final diagram.
