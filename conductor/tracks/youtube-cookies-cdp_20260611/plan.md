# Implementation Plan: YouTube Cookies via CDP

## Phase 1: Enable CDP on BrowserOS
- [x] Task: Restart BrowserOS with `--remote-allow-origins=*` flag
  - Modify systemd service or wrapper script
  - Verify CDP port 9108 accessible

## Phase 2: Cookie Extraction
- [x] Task: Write Python script to connect to CDP WebSocket
  - Connect to `ws://127.0.0.1:9108/devtools/page/{id}`
  - Call `Network.getAllCookies`
  - Filter YouTube/Google domains
  - Export Netscape format to `/tmp/yt-cookies.txt`

## Phase 3: Transfer & Integration
- [x] Task: Copy cookies to RPi: `scp /tmp/yt-cookies.txt rpi:~/rpi-dashboard/yt-cookies.txt`
- [x] Task: Update `webserver_8099.py` resolve() to use `cookiefile` parameter
- [x] Task: Update yt-dlp to v2026.06.09

## Phase 4: Validation
- [x] Task: Test age-restricted video (Rick Astley)
- [x] Task: Test regular video
- [x] Conductor - User Manual Verification 'youtube-cookies-cdp'