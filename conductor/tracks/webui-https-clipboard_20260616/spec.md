# Specification: HTTPS WebUI for clipboard support

## Overview
Enable HTTPS for the RPi Dashboard WebUI so browser Clipboard API can work in a secure context. Keep the current HTTP endpoint for compatibility, and add an HTTPS endpoint with a locally generated self-signed certificate.

## Functional Requirements
- Serve the existing WebUI over HTTPS on a dedicated port.
- Keep HTTP `:8099` working for compatibility.
- Generate a local self-signed certificate automatically if none exists.
- Do not commit private keys or generated certificates.
- Surface the HTTPS URL in logs and WebUI diagnostics where practical.
- Clipboard paste button should work on HTTPS-capable browsers after certificate acceptance / permission.

## Acceptance Criteria
- `https://192.168.0.205:<port>/` returns the WebUI.
- HTTP `http://192.168.0.205:8099/` still returns the WebUI.
- Remote Playwright verification uses HTTPS with certificate errors ignored and verifies the Player UI.
- Clipboard API presence is verified in the HTTPS browser context.
- CI and `tools/verify-done.sh` pass.

## Out of Scope
- Public trusted certificates / domain setup.
- Replacing the existing 8099 HTTP endpoint.
