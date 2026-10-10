# Implementation Plan: Friendly WebUI ports and hostnames

## Phase 1 — Design
- [x] Confirm HTTP and HTTPS require separate default ports: 80 and 443
- [x] Confirm privileged bind needs systemd capability rather than root service

## Phase 2 — Code
- [x] Add standard HTTP/HTTPS ports while preserving compatibility ports
- [x] Improve certificate SAN generation for LAN/Tailnet hostnames/IPs
- [x] Update HTTPS info endpoint with friendly URLs

## Phase 3 — Systemd
- [x] Add runtime systemd capability override for low ports
- [x] Restart and verify service user remains non-root

## Phase 4 — Verification
- [x] Verify local HTTP/HTTPS standard ports and compatibility ports
- [x] Verify remote Playwright over HTTPS default port with clipboard API
- [x] Run finish pipeline and verify-done

## Verification Evidence
- Runtime systemd drop-in: `/etc/systemd/system/webserver-8099.service.d/10-bind-low-ports.conf` with `CAP_NET_BIND_SERVICE`.
- Service user after restart: `milhy777`.
- Local listeners: `:80`, `:443`, `:8099`, `:8443`.
- Local checks: `http://127.0.0.1/`, `https://127.0.0.1/system/https-info`, `http://127.0.0.1:8099/system/https-info`, `https://127.0.0.1:8443/system/https-info`.
- Remote host: Milhy-PC.
- Remote checks: `http://rpi/`, `https://rpi/`, `https://rpi.local/`, `https://192.168.0.205/`.
- Remote Playwright artifact: `/tmp/rpi-dashboard-webapp-artifacts/webapp-test-friendly-20260616-133428/`.
- Browser results: HTTPS secure context true, clipboard API present, quality `720p`, paste button `📋`, no console errors.
