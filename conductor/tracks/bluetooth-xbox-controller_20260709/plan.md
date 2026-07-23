# Plan: Bluetooth Pairing and Xbox Controller Support

## Status

Done — superseded by `bluetooth-control-center-refactor_20260718`. Live
verification on 2026-07-23 confirmed that the paired Xbox controller is
connected, trusted, services-resolved, visible through Linux input devices,
and reports no Steam Link readiness blockers.

## Steps

1. Unify Bluetooth backend data.
   - Normalize paired, scanned, connected, and trusted devices in
     `rpi_dashboard.services.devices`.
   - Add controller readiness diagnostics for Xbox and Steam Link.
   - Keep legacy endpoints compatible while returning richer fields.

2. Add WebUI Bluetooth surface.
   - Add a main-menu Bluetooth tab using existing theme/card styles.
   - Reuse the same device card order and actions as TUI.
   - Keep Devices focused on Wi-Fi and hardware role notes.

3. Add TUI Bluetooth surface.
   - Move Bluetooth from Devices into its own top-level tab.
   - Render normalized devices with the same role/status/action model.
   - Use the shared service layer through async wrappers instead of raw parsing.

4. Add Xbox/Steam Link support checks.
   - Detect Xbox controllers from Bluetooth names.
   - Report ERTM, likely driver/module state, input devices, and Steam Link
     command availability.
   - Provide a clear preflight view before launching Steam Link.

5. Verify and finish through Conductor.
   - Run focused tests, then full `ruff`, `mypy`, and `pytest`.
   - Restart `dashboard@milhy777.service` and smoke-check TUI/WebUI endpoints.
   - Commit only via `tools/finish-track.sh`.
