# Implementation Plan: DLNA Scan

## Phase 1: Install Tools
- [x] Task: Install `gupnp-tools` package (`apt install gupnp-tools`)

## Phase 2: Backend Endpoint
- [x] Task: Add `/dlna/scan` endpoint to webserver_8099.py
  - Run `gssdp-discover -n 5 -t urn:schemas-upnp-org:device:MediaRenderer:1`
  - Parse output for USN and Location
  - Filter for MediaRenderer devices
  - Return JSON with devices array and count

## Phase 3: Frontend
- [x] Task: Add DLNA section to Audio tab in webUI
  - Scan button
  - Status display
  - Results list

## Phase 4: Validation
- [x] Test scan finds 2 MediaRenderers (LG TV + WiiMu)
- [x] Test via webUI
- [x] Conductor - User Manual Verification 'dlna-scan'