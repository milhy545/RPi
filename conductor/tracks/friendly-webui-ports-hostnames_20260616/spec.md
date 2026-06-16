# Specification: Friendly WebUI ports and hostnames

## Overview
Make the dashboard easier to open from LAN and Tailnet by serving standard web ports in addition to compatibility ports. Users should be able to type a simple host URL instead of remembering 8099/8443.

## Requirements
- Keep compatibility HTTP `:8099` and HTTPS `:8443` working.
- Add standard HTTP `:80`.
- Add standard HTTPS `:443` for secure-context Clipboard API.
- Generate self-signed certificate SANs for current hostnames/IPs where possible: `rpi`, `rpi.local`, localhost, LAN IPv4, Tailscale IPv4/IPv6.
- Systemd must allow the non-root webserver process to bind privileged ports without running the whole service as root.
- `/system/https-info` should advertise friendly URLs.
- Verify both local and remote browser access.

## Acceptance Criteria
- `http://192.168.0.205/` returns the WebUI.
- `https://192.168.0.205/` returns the WebUI after accepting self-signed cert.
- Compatibility URLs still work.
- Remote Playwright verifies HTTPS default port secure context and Clipboard API.
- Service still runs as `milhy777`.
- CI and `tools/verify-done.sh` pass.

## Notes
- HTTP and HTTPS cannot both be served on the same TCP port in normal browsers. The friendly setup is HTTP on default port 80 and HTTPS on default port 443.
