# Workflow: RPi Dumb TV Dashboard

## 1. Development Cycle

### 1.1 Local Development
1. Vývoj a úpravy TUI kódu na Milhy-PC.
2. Správa závislostí výhradně přes `uv`.
3. Lokální unit testy přes `pytest`.

### 1.2 QEMU Validation
1. Spustit RPi OS v QEMU na lokálním stroji.
2. Nasadit TUI do emulovaného prostředí (rsync/chroot).
3. Ověřit funkčnost v ARM prostředí — TUI rendering, systemd integrace, síťový listener.
4. Ověřit RAM spotřebu (musí být ≤ 20 MB pro core TUI).

### 1.3 Deploy to Real RPi
1. Po úspěšné QEMU validaci nasadit na reálné RPi přes SSH/rsync.
2. Restart systemd service.
3. Smoke test na TV.

## 2. Branching Strategy
- **main:** Stabilní, deployovatelný kód.
- **dev:** Aktivní vývoj.
- Feature branches dle potřeby.

## 3. Code Quality
- **Linting:** `ruff check` před každým commitem.
- **Formatting:** `ruff format`.
- **Testy:** `pytest` pro unit testy.
- **TUI dev:** `textual-dev` pro vizuální debugování.

## 4. Commit Conventions
- Formát: `type(scope): message`
- Typy: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`
- Scope: `tui`, `network`, `modes`, `qemu`, `deploy`

## 5. Task Management
- Conductor tracks pro plánování a sledování.
- Inkrementální vývoj — malé logické bloky, žádné mega-commity.
