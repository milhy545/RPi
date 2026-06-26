# TODO — RPi-TV Dashboard System Overhaul

> Created: 2026-06-26
> Source: Multi-Agent Code Review + System Audit

---

## Phase 0: Repo Cleanup
- [ ] Zkontrolovat Jules open tasks
- [ ] Vyřešit merge conflicts PR #20
- [ ] Merge PR #15 (yt_id tests)
- [ ] Merge PR #20 (unused imports)
- [ ] Ověřit GH Actions green
- [ ] Smazat merged branches
- [ ] Sync local = remote
- [ ] Rename master → main (pokudANO)

## Phase 1: Critical Fixes
- [ ] 37x bare `except:` → `except Exception:`
- [ ] Resource leaky (json.load/open)
- [ ] WebSocket auth
- [ ] File context managery

## Phase 2: Rename & Ports
- [ ] Rename webserver_8099.py → webserver.py
- [ ] Update imports/references
- [ ] Přidat porty 80, 8080, 443, 8443
- [ ] Update systemd units
- [ ] Test na všech portech

## Phase 3: Code Quality
- [ ] Type hints
- [ ] Magic numbers → constants
- [ ] English comments
- [ ] Docstrings
- [ ] pytest testy

## Phase 4: Security
- [ ] WiFi heslo bez cmdline
- [ ] Rate limiting
- [ ] CORS
- [ ] HTTPS automation

## Phase 5: Open Tracks
- [ ] webui-report-conductor-intake
- [ ] webui-czech-completion
- [ ] dashboard-modes-settings-terminal
