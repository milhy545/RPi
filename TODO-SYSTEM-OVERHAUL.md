# TODO — RPi-TV Dashboard System Overhaul

> Created: 2026-06-26
> Source: Multi-Agent Code Review + System Audit

---

## Phase 0: Repo Cleanup
- [x] Zkontrolovat Jules open tasks
- [x] Vyřešit merge conflicts PR #20
- [x] Merge PR #15 (yt_id tests)
- [x] Merge PR #20 (unused imports)
- [x] Ověřit GH Actions green
- [x] Smazat merged branches
- [x] Sync local = remote
- [x] Rename master → main (pokudANO)

## Phase 1: Critical Fixes
- [x] 37x bare `except:` → `except Exception:`
- [x] Resource leaky (json.load/open)
- [x] WebSocket auth
- [x] File context managery

## Phase 2: Rename & Ports
- [x] Rename webserver_8099.py → webserver.py
- [x] Update imports/references
- [x] Přidat porty 80, 8080, 443, 8443
- [x] Update systemd units
- [x] Test na všech portech

## Phase 3: Code Quality
- [x] Type hints
- [x] Magic numbers → constants
- [x] English comments
- [x] Docstrings
- [x] pytest testy

## Phase 4: Security
- [x] WiFi heslo bez cmdline
- [x] Rate limiting
- [x] CORS
- [x] HTTPS automation

## Phase 5: Open Tracks
- [x] webui-report-conductor-intake
- [x] webui-czech-completion
- [x] dashboard-modes-settings-terminal
- [ ] android-share-app
- [ ] smart-home-integrations
