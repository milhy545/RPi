# Implementation Plan: RPi-TV Dashboard System Overhaul

> Archived 2026-07-23 after evidence reconciliation. This umbrella plan is
> superseded by focused tracks. Checked items indicate verified current
> behavior or a documented handoff to `dashboard-security-cleanup_20260723`,
> `backend-modularization-completion_20260723`, and
> `verification-coverage-hardening_20260723`; they do not claim that every
> original implementation idea was adopted literally.

## Scope
- In: Code review fixes, rename webserver, standard ports, repo cleanup, Jules PR merge
- Out: New features (Android share, smart home), TUI rewrite

---

## Phase 0: Repo Cleanup (před jakýmkoliv kódem)

- [x] **0.1** Zkontrolovat Jules open tasks — PR #20 (unused imports) a PR #15 (yt_id tests)
- [x] **0.2** Vyřešit merge conflicts v PR #20 (CONFLICTING) — rebase na master
- [x] **0.3** Merge PR #15 (yt_id tests) do main — checks OK
- [x] **0.4** Merge PR #20 (unused imports) do main — po rebase
- [x] **0.5** Ověřit všechny GH Actions green — `gh run list --limit 10`
- [x] **0.6** Smazat všechny merged branches kromě main/master — `git branch -d`
- [x] **0.7** Sync local repo s remote — `git fetch origin && git reset --hard origin/main`
- [x] **0.8** Rename `master` → `main` pokud je to cílový název

---

## Phase 1: Code Review — Critical Fixes

- [x] **1.1** Nahradit 37x bare `except:` za `except Exception:` (webserver)
- [x] **1.2** Opravit resource leaky — `json.load(open(...))` → context managery (webserver:595,601)
- [x] **1.3** Přidat auth na WebSocket terminal (ws://rpi-tv:8098)
- [x] **1.4** Uzavírat soubory přes `with` v/audio/dlna funkcích

---

## Phase 2: Rename & Restructure

- [x] **2.1** Rename `webserver_8099.py` → `webserver.py`
- [x] **2.2** Update všech importů/referencí (tui.py, tests, systemd units)
- [x] **2.3** Update `RPIDASHBOARD_API_PORT` env var default
- [x] **2.4** Přidat standardní porty — 80, 8080, 443, 8443 (HTTP + HTTPS)
- [x] **2.5** Update systemd service soubory pro nový název + porty
- [x] **2.6** Test: spustit webserver na všech portech, ověřit WebUI

---

## Phase 3: Code Quality

- [x] **3.1** Přidat type hints postupně (začít od veřejných funkcí)
- [x] **3.2** Nahradit magic numbers konstantami
- [x] **3.3** Standardizovat komentáře na English
- [x] **3.4** Přidat docstringy na hlavní funkce
- [x] **3.5** Založit `tests/` strukturu s pytest

---

## Phase 4: Security Hardening

- [x] **4.1** WiFi heslo — používat `subprocess.run(..., input=password)` místo cmdline
- [x] **4.2** Přidat rate limiting na API endpoints
- [x] **4.3** CORS headers — omezit na localhost/LAN
- [x] **4.4** HTTPS certifikáty — automatizace s Let's Encrypt nebo self-signed

---

## Phase 5: Open Track Activation

- [x] **5.1** `webui-report-conductor-intake` — WebUI bug/feature modal
- [x] **5.2** `webui-czech-completion` — Dokončit české překlady
- [x] **5.3** `dashboard-modes-settings-terminal` — Obnovit parity

---

## Open Questions
- Chceš rename `master` → `main` nebo ponechat `master`?
- WebSocket auth — API key v query param, nebo HMAC token?
- Standardní porty — bindovat všechny najednou, nebo jen vybrané?
