# Specification: DLNA Scan

## Goal
Discover DLNA/UPnP MediaRenderers on the local network via SSDP and display them in the webUI.

## Implementation
- **Tool:** `gssdp-discover` (from `gupnp-tools` package)
- **Target:** `urn:schemas-upnp-org:device:MediaRenderer:1`
- **Timeout:** 5 seconds
- **Output:** Parse USN and Location, filter for MediaRenderer

## API Endpoint
- `GET /dlna/scan` → returns JSON with devices array and count

## WebUI Integration
- **Audio Tab:** DLNA section with Scan button
- **Results:** List renderers with USN and Location
- **Status:** Shows count of found renderers

## Acceptance Criteria
- [ ] `gssdp-discover` finds 2 MediaRenderers (LG TV + WiiMu)
- [ ] `/dlna/scan` returns JSON with device list
- [ ] WebUI shows DLNA section with Scan button
- [ ] Results display USN and Location
- [ ] Scan completes within 10 seconds