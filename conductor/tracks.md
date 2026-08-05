# Tracks Registry
# Updated after closing audio-fullstack-refactor track

<!-- Register new tracks below. Format: - [ ] **Track: <id>** — <description> | [Plan](./tracks/<id>/plan.md) -->

- [ ] **Track: rpi-safe-ci-workflow_20260805** — Safe RPi / Milhy-PC / Jules Validation Pipeline & Execution Profiles | [Plan](./tracks/rpi-safe-ci-workflow_20260805/plan.md)

- [x] **Track: network-cast-api** — Network Cast API (Port 8099) — merged into WebUI / mode-switcher | [Plan](./tracks/network-cast-api_20260602/plan.md)
- [x] **Track: automated-provisioning** — Automated Provisioning (Ansible/Shell) — done; superseded by live stack baseline | [Plan](./tracks/automated-provisioning_20260602/plan.md)
- [x] **Track: mode-switcher-engine** — Zero-Overhead Mode Switcher Engine (TUI suspension, subprocess spawning & recovery) — done; UI parity leftovers tracked elsewhere | [Plan](./tracks/mode-switcher-engine/plan.md)
- [x] **Track: devices-connections** — Devices & Connections Management (Audio output, Bluetooth pairing, Wi-Fi configuration, Tailscale info) | [Plan](./tracks/devices-connections/plan.md)
- [x] **Track: youtube-cookies-cdp** — YouTube Cookies via CDP (BrowserOS on Milhy-PC, 61 cookies, age-restricted videos) | [Plan](./tracks/youtube-cookies-cdp_20260611/plan.md)
- [x] **Track: cec-controls** — CEC Controls (Power, Navigation, Volume, Bridge, Input Switching) | [Plan](./tracks/cec-controls_20260611/plan.md)
- [x] **Track: terminal-tab-webui** — Terminal Tab in WebUI (WebSocket 8098 → tmux RPi:1, xterm.js) | [Plan](./tracks/terminal-tab-webui_20260611/plan.md)
- [x] **Track: dlna-scan** — DLNA Scan (gssdp-discover, 2 MediaRenderers found) | [Plan](./tracks/dlna-scan_20260611/plan.md)
- [x] **Track: bt-audio-loopback** — Bluetooth Audio Loopback (USB Input → BT Soundbar via PipeWire) — done | [Plan](./tracks/bt-audio-loopback_20260611/plan.md)
- [x] **Track: mpv-keep-open-fix** — mpv --keep-open=always Fix (prevents socket freeze on video end) | [Plan](./tracks/mpv-keep-open-fix_20260611/plan.md)
- [x] **Track: cpuset-monitor-fix** — Fix cpuset-monitor Bug (pins mpv to wrong cores on start) | [Plan](./tracks/cpuset-monitor-fix_20260611/plan.md)
- [x] **Track: dlna-rendering** — DLNA/UPnP Rendering (gmrender-resurrect or Kodi headless) | [Plan](./tracks/dlna-rendering_20260611/plan.md)
- [x] **Track: playback-resume-memory** — Remember interrupted playback position and offer WebUI resume prompt | [Plan](./tracks/playback-resume-memory_20260613/plan.md)
- [x] **Track: safe-webserver-restart** — Restart WebUI server without unlinking active mpv IPC socket | [Plan](./tracks/safe-webserver-restart_20260613/plan.md)
- [x] **Track: git-live-dev-workflow** — Make RPi live tree the development Git repo, Milhy-PC push gateway | [Plan](./tracks/git-live-dev-workflow_20260613/plan.md)
- [x] **Track: audio-tab-refactor** — Refine Test Audio prototype before replacing stable Audio tab | [Plan](./tracks/audio-tab-refactor_20260613/plan.md)
- [x] **Track: audio-routing-mixer-v2** — HDMI-first audio mixer with DLNA input/output and latency controls — done; merged into stable Audio | [Plan](./tracks/audio-routing-mixer-v2_20260613/plan.md)
- [x] **Track: webui-report-conductor-intake** — WebUI bug/feature modal that creates draft Conductor tracks | [Plan](./tracks/webui-report-conductor-intake_20260613/plan.md)
- [x] **Track: test-audio-hardening** — Harden Test Audio WebUI validation, keepalive cleanup, escaping, and self-tests | [Plan](./tracks/test-audio-hardening_20260613/plan.md)
- [x] **Track: test-audio-review-fixes** — Layout-preserving Test Audio fixes discovered during review | [Plan](./tracks/test-audio-review-fixes_20260613/plan.md)
- [x] **Track: audio-devices-age-routes** — Promote Audio, add Devices, and add YouTube age diagnostics | [Plan](./tracks/audio-devices-age-routes_20260613/plan.md)
- [x] **Track: project-docs-reference** — Complete project documentation reference | [Plan](./tracks/project-docs-reference_20260613/plan.md)
- [x] **Track: webui-bilingual-i18n** — Add Czech/English WebUI switch with flags | [Plan](./tracks/webui-bilingual-i18n_20260613/plan.md)
- [x] **Track: webui-czech-completion** — Add missing EN/CZ translations in WebUI — completed | [Plan](./tracks/webui-czech-completion_20260613/plan.md)
- [x] **Track: player-preview-clipboard** — Player thumbnail and clipboard paste | [Plan](./tracks/player-preview-clipboard_20260613/plan.md)
- [ ] **Track: android-share-app_20260613** — Android share-target PWA is present; native companion app and device verification remain open | [Plan](./tracks/android-share-app_20260613/plan.md)
- [ ] **Track: smart-home-integrations** — Home Assistant REST/MQTT bridge integration remains partially implemented | [Plan](./tracks/smart-home-integrations_20260613/plan.md)
- [x] **Track: alexa-dlna-audio-routing** — Alexa and DLNA audio routing | [Plan](./tracks/alexa-dlna-audio-routing_20260613/plan.md)
- [x] **Track: devices-tab-hardening** — Finish and tune Devices tab | [Plan](./tracks/devices-tab-hardening_20260613/plan.md)
- [x] **Track: terminal-hw-stats** — Terminal tab fixes and hardware stats | [Plan](./tracks/terminal-hw-stats_20260613/plan.md)
- [x] **Track: kodi-tab-decision** — Evaluate Kodi tab usefulness | [Plan](./tracks/kodi-tab-decision_20260613/plan.md)
- [x] **Track: dashboard-modes-settings-terminal** — Restore Dashboard TUI modes/settings parity | [Plan](./tracks/dashboard-modes-settings-terminal_20260613/plan.md)
- [x] **Track: ci-gateway-milhy-pc** — Milhy-PC CI gateway for safe RPi commits and GitHub push | [Plan](./tracks/ci-gateway-milhy-pc_20260614/plan.md)
- [x] **Track: restart-stale-mpv-preview-autoload** — Restart stale mpv and automatic player preview | [Plan](./tracks/restart-stale-mpv-preview-autoload_20260616/plan.md)
- [x] **Track: player-clipboard-autoload** — Player clipboard autoload reliability | [Plan](./tracks/player-clipboard-autoload_20260616/plan.md)
- [x] **Track: player-paste-button-default-720** — Player paste button and 720p default | [Plan](./tracks/player-paste-button-default-720_20260616/plan.md)
- [x] **Track: player-paste-inside-input** — Player paste button inside URL input | [Plan](./tracks/player-paste-inside-input_20260616/plan.md)
- [x] **Track: webui-https-clipboard** — HTTPS WebUI for clipboard support | [Plan](./tracks/webui-https-clipboard_20260616/plan.md)
- [x] **Track: friendly-webui-ports-hostnames** — Friendly WebUI ports and hostnames | [Plan](./tracks/friendly-webui-ports-hostnames_20260616/plan.md)
- [x] **Track: http-https-fallback-banner** — HTTP fallback with HTTPS clipboard banner | [Plan](./tracks/http-https-fallback-banner_20260616/plan.md)
- [x] **Track: remove-kodi-tab** — Remove Kodi tab from WebUI | [Plan](./tracks/remove-kodi-tab_20260616/plan.md)
- [ ] **Track: mpv-optimization-20260627** — Runtime measurement and target-device optimization verification remain open | [Plan](./tracks/mpv-optimization-20260627/plan.md)

- [x] **Track: report_1782888036_feature** — Audio Matrix Patchbay (DLNA loopback support) | [Plan](./tracks/report_1782888036_feature/plan.md)

- [x] **Track: report_1782888573_feature** — Feature report (incorporated into refactor-fullstack_20260706) | [Plan](./tracks/report_1782888573_feature/plan.md)

- [x] **Track: report_1782888498_bug** — Bug report (incorporated into refactor-fullstack_20260706) | [Plan](./tracks/report_1782888498_bug/plan.md)

- [x] **Track: refactor-fullstack_20260706** — Full-Stack Refactoring: Backend modularization + WebUI responsive + TUI modernization | [Plan](./tracks/refactor-fullstack_20260706/plan.md)
- [x] **Track: bluetooth-xbox-controller_20260709** — Superseded by Bluetooth Control Center; paired Xbox controller readiness verified live on 2026-07-23 | [Plan](./tracks/bluetooth-xbox-controller_20260709/plan.md)
- [x] **Track: bluetooth-control-center-refactor_20260718** — Multi-adapter BlueZ Bluetooth control center with stable identity, WebUI/TUI parity, hotplug, diagnostics, soundbar, and Xbox/Steam Link readiness | [Plan](./tracks/bluetooth-control-center-refactor_20260718/plan.md)
- [x] **Track: bluetooth-tui-control-center-parity_20260719** — Make the live TUI Bluetooth tab and BT WebUI settings match the saved control center references | [Plan](./tracks/bluetooth-tui-control-center-parity_20260719/plan.md)

- [x] **Track: system-overhaul_20260626** — Archived umbrella; residual work split into focused security, backend, and verification tracks | [Plan](./tracks/system-overhaul_20260626/plan.md)
- [ ] **Track: milhy-pc-firewall_20260611** — Default-deny Milhy-PC firewall still requires live host verification | [Plan](./tracks/milhy-pc-firewall_20260611/plan.md)
- [x] **Track: bluetooth-dbus-live-events_20260723** — Complete two-adapter Bluetooth hub with Windows/Linux profiles, audio/headset/control, OBEX files, and autoconnect | [Plan](./tracks/bluetooth-dbus-live-events_20260723/plan.md)
- [x] **Track: dashboard-security-cleanup_20260723** — Move Wi-Fi settings to Network and close credential, WebSocket, and static-analysis security gaps — all phases verified complete | [Plan](./tracks/dashboard-security-cleanup_20260723/plan.md)
- [x] **Track: backend-modularization-completion_20260723** — Finish modularization, redesign production WebUI/TUI, and retire legacy endpoints through migration — **completed 2026-08-04** | [Plan](./tracks/backend-modularization-completion_20260723/plan.md)
- [x] **Track: unified-ui-ux-refactor_20260728** — Implementation is present; four documented Playwright viewport captures captured; receipt pending final finish-track pass | [Plan](./tracks/unified-ui-ux-refactor_20260728/plan.md)
- [x] **Track: lightweight-auth-boundaries_20260729** — Role-based access control with Basic/Expert/Admin tiers, session management, CSRF protection, and local CLI provisioning (depends: dashboard-security-cleanup_20260723; blocks: unified-ui-ux-refactor_20260728) | [Plan](./tracks/lightweight-auth-boundaries_20260729/plan.md)
- [ ] **Track: verification-coverage-hardening_20260723** — Resolve audited failures, optimize measured runtime behavior, and strengthen coverage/verification | [Plan](./tracks/verification-coverage-hardening_20260723/plan.md)
- [ ] **Track: mpv-eof-runtime-return_20260723** — Implementation exists; target-device EOF, keyboard, and Xbox verification remain open | [Plan](./tracks/mpv-eof-runtime-return_20260723/plan.md)

- [x] **Track: report_1784787193_bug** — HDMI Audio Mixer Routing Fix — module-loopback for non-player sources | [Plan](./tracks/report_1784787193_bug/plan.md)
- [x] **Track: bluetooth-setup-wizard_20260724** — Bluetooth Setup Wizard | [Plan](./tracks/bluetooth-setup-wizard_20260724/plan.md)
- [x] **Track: multi-output-audio-mpv_20260725** — Multi-Output Audio Distribution for BT Source (Realme 8) & MPV Player | [Plan](./tracks/multi-output-audio-mpv_20260725/plan.md)
- [x] **Track: audio-fullstack-refactor_20260725** — Audio modularization done; BT sync transferred to bt-dbus-resilience; remaining: TUI flow diagram, WebUI topology polish, test coverage | [Plan](./tracks/audio-fullstack-refactor_20260725/plan.md)


- [x] **Track: audio-multimixer-webui_20260725** — Absorbed into audio-fullstack-refactor_20260725 | [Plan](./tracks/audio-multimixer-webui_20260725/plan.md)

- [x] **Track: report_1785101816_bug** — Bug report | [Plan](./tracks/report_1785101816_bug/plan.md)
- [ ] **Track: keys2mpv-input-device-hardening_20260727** — Implementation is present; target-RPi input discovery and runtime verification remain open | [Plan](./tracks/keys2mpv-input-device-hardening_20260727/plan.md)

- [x] **Track: report_1785203244_bug** — BT volume sync — absorbed into audio-fullstack-refactor_20260725 | [Plan](./tracks/report_1785203244_bug/plan.md)

- [x] **Track: modular_test_ci_config_audio_fix_20260626** — Archived umbrella; remaining modularization, CI, coverage, and audio work is tracked by focused successor tracks | [Plan](./tracks/modular_test_ci_config_audio_fix_20260626/plan.md)
- [ ] **Track: bt-dbus-resilience_20260804** — BT D-Bus Resilience & Multi-Speaker Stability: crash recovery, adapter profiling, codec lock engine, Playwright E2E | [Plan](./tracks/bt-dbus-resilience_20260804/plan.md)
