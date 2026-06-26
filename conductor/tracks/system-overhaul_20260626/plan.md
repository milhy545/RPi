# Implementation Plan: RPi-TV Dashboard System Overhaul

## Scope
- In: Code review fixes, rename webserver, standard ports, repo cleanup, Jules PR merge
- Out: New features (Android share, smart home), TUI rewrite

---

## Phase 0: Repo Cleanup (před jakýmkoliv kódem)

- [ ] **0.1** Zkontrolovat Jules open tasks — PR #20 (unused imports) a PR #15 (yt_id tests)
- [ ] **0.2** Vyřešit merge conflicts v PR #20 (CONFLICTING) — rebase na master
- [ ] **0.3** Merge PR #15 (yt_id tests) do main — checks OK
- [ ] **0.4** Merge PR #20 (unused imports) do main — po rebase
- [ ] **0.5** Ověřit všechny GH Actions green — `gh run list --limit 10`
- [ ] **0.6** Smazat všechny merged branches kromě main/master — `git branch -d`
- [ ] **0.7** Sync local repo s remote — `git fetch origin && git reset --hard origin/main`
- [ ] **0.8** Rename `master` → `main` pokud je to cílový název

---

## Phase 1: Code Review — Critical Fixes

- [ ] **1.1** Nahradit 37x bare `except:` za `except Exception:` (webserver)
- [ ] **1.2** Opravit resource leaky — `json.load(open(...))` → context managery (webserver:595,601)
- [ ] **1.3** Přidat auth na WebSocket terminal (ws://rpi-tv:8098)
- [ ] **1.4** Uzavírat soubory přes `with` v/audio/dlna funkcích

---

## Phase 2: Rename & Restructure

- [ ] **2.1** Rename `webserver_8099.py` → `webserver.py`
- [ ] **2.2** Update všech importů/referencí (tui.py, tests, systemd units)
- [ ] **2.3** Update `RPIDASHBOARD_API_PORT` env var default
- [ ] **2.4** Přidat standardní porty — 80, 8080, 443, 8443 (HTTP + HTTPS)
- [ ] **2.5** Update systemd service soubory pro nový název + porty
- [ ] **2.6** Test: spustit webserver na všech portech, ověřit WebUI

---

## Phase 3: Code Quality

- [ ] **3.1** Přidat type hints postupně (začít od veřejných funkcí)
- [ ] **3.2** Nahradit magic numbers konstantami
- [ ] **3.3** Standardizovat komentáře na English
- [ ] **3.4** Přidat docstringy na hlavní funkce
- [ ] **3.5** Založit `tests/` strukturu s pytest

---

## Phase 4: Security Hardening

- [ ] **4.1** WiFi heslo — používat `subprocess.run(..., input=password)` místo cmdline
- [ ] **4.2** Přidat rate limiting na API endpoints
- [ ] **4.3** CORS headers — omezit na localhost/LAN
- [ ] **4.4** HTTPS certifikáty — automatizace s Let's Encrypt nebo self-signed

---

## Phase 5: Open Track Activation

- [ ] **5.1** `webui-report-conductor-intake` — WebUI bug/feature modal
- [ ] **5.2** `webui-czech-completion` — Dokončit české překlady
- [ ] **5.3** `dashboard-modes-settings-terminal` — Obnovit parity

---

## Open Questions
- Chceš rename `master` → `main` nebo ponechat `master`?
- WebSocket auth — API key v query param, nebo HMAC token?
- Standardní porty — bindovat všechny najednou, nebo jen vybrané?
