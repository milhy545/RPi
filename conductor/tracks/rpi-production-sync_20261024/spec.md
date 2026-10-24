# Track Specification: RPi Production Repository Synchronization

## Goal

Reconcile the Raspberry Pi production checkout with the current GitHub `main` without losing current user work or changing machine-specific playback settings.

## Requirements

- Verify the SSH target and record its live address in `~/.gemini/GEMINI.md`.
- Preserve the RPi commit history, dirty files, and local configuration before changing the production checkout.
- Treat current GitHub `main` as the source of application and CI truth. Do not merge the closed PR #85 snapshot wholesale: its stale tree would remove current tests and CI protections.
- Keep `.dlnain-mode.json` as local machine state; do not publish the RPi manual sink selection to the shared repository.
- Preserve the two currently uncommitted report entries because the user explicitly requested that current RPi work be synchronized.
- Push and merge only from Milhy-PC after the normal branch checks and Kilo review pass. RPi never pushes.
- Update the RPi checkout only after the exact commit is on GitHub `main`; do not restart services or interrupt playback.
- Notify the user for manual application verification. Do not delete branches before the user confirms that test.

## Acceptance Criteria

- The address record matches the host verified through the `RPi` SSH alias.
- A verified backup exists for the pre-sync RPi commit and dirty files.
- The requested report entries are present on GitHub `main`, without reverting current main code, tests, or CI.
- The RPi checkout points at the exact GitHub `main` SHA, with local audio mode preserved.
- No push was performed from RPi, and no services were restarted.
- The user has been told that manual verification is pending; branch cleanup remains deferred.
