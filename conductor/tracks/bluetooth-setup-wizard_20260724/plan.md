# Plan

- [x] 1. **Default View**: Update frontend JS/HTML to make the initial state of the Bluetooth tab "Basic" instead of "Advanced".
- [x] 2. **Backend API (Reset)**: Implement an endpoint to cleanly unpair all devices across all adapters and reset BT state.
- [x] 3. **Backend API (Capabilities)**: Implement logic to distinguish USB vs. UART adapters to recommend the optimal adapter for audio.
- [x] 4. **Backend API (Isolated Pairing)**: Extend the pairing API to start discovery and accept pairings exclusively on a specified adapter.
- [x] 5. **Backend API (Phone Role)**: Add logic to classify/configure a paired phone as either an audio source (A2DP source) or sink (A2DP sink).
- [x] 6. **Frontend Wizard (Structure)**: Create the Wizard modal component with a 5-step navigation skeleton.
- [x] 7. **Frontend Wizard (Steps 1 & 2)**: Implement the UI for Step 1 (Warning/Reset) and Step 2 (Adapter Selection).
- [x] 8. **Frontend Wizard (Steps 3 & 4)**: Implement the UI for Step 3 (IO Pairing) and Step 4 (Audio Pairing with Phone role prompt).
- [x] 9. **Frontend Wizard (Step 5)**: Implement the final Summary step, reusing the topology diagram component, with Confirm/Back actions.
