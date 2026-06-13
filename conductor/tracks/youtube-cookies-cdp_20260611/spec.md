# Specification: YouTube Cookies via CDP

## Goal
Extract authenticated YouTube cookies from BrowserOS on Milhy-PC via Chrome DevTools Protocol (CDP) to enable age-restricted video playback on RPi via yt-dlp.

## Problem
- yt-dlp needs authenticated cookies for age-restricted videos
- BrowserOS on Milhy-PC has user logged into YouTube
- Standard `--cookies-from-browser` fails due to v11 encryption + non-standard profile path

## Solution
1. Enable CDP on BrowserOS with `--remote-allow-origins=*`
2. Connect via WebSocket to CDP port 9108
3. Call `Network.getAllCookies` to get ALL cookies (including httpOnly)
4. Filter for YouTube/Google domains
5. Export to Netscape format `yt-cookies.txt`
4. Copy to RPi, configure yt-dlp `cookiefile` parameter

## Acceptance Criteria
- [ ] 61+ cookies extracted (including HSID, SSID, SID, SAPISID, APISID, __Secure-1PSID)
- [ ] Age-restricted YouTube videos play on RPi via webUI
- [ ] Cookies file at `~/rpi-dashboard/yt-cookies.txt`
- [ ] yt-dlp uses `cookiefile` parameter in resolve()