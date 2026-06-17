# Repository Guidelines

## Project Structure & Module Organization

This repository is a small Python 3.12 project for Raspberry Pi tooling and a
Textual-based dashboard. `main.py` is the minimal CLI entry point, while
`tui.py` contains the current interactive dashboard prototype. Shell helpers
`chroot-mount.sh` and `chroot-umount.sh` manage a local `rootfs/` chroot, which
is intentionally ignored by git. `qemu/` stores the compressed RPi OS image
asset. Project planning, product notes, workflow guidance, and code style
references live under `conductor/`.

## Build, Test, and Development Commands

- `uv sync` installs the Python dependencies from `pyproject.toml` and
  `uv.lock`.
- `uv run python main.py` runs the simple CLI entry point.
- `uv run python tui.py` starts the Textual dashboard.
- `bash chroot-mount.sh` mounts the local `rootfs/` for chroot work; run
  `bash chroot-umount.sh` before leaving the workspace or switching tasks.

There is no Makefile and no committed test suite yet, so do not document or
claim broader automation until it exists.

## Coding Style & Naming Conventions

Use 4-space indentation for Python and keep code readable before clever. Follow
the project style notes in `conductor/code_styleguides/python.md`: `snake_case`
for functions and variables, `PascalCase` for classes, and
`ALL_CAPS_WITH_UNDERSCORES` for constants. Prefer type annotations for public
APIs and keep imports grouped as standard library, third-party, then local
modules. For shell scripts, keep commands explicit and quote variables such as
`"$ROOTFS_DIR"`.

## Testing Guidelines

No testing framework is configured yet. When adding behaviour, create focused
tests before expanding features; `pytest` is the preferred default unless the
project adopts another tool. Name tests after behaviour, for example
`tests/test_tui_modes.py`. Until tests exist, verify changes manually with
`uv run python main.py`, `uv run python tui.py`, and the relevant chroot helper
flow.

## Commit & Pull Request Guidelines

This checkout has no commit history, so establish concise Conventional
Commit-style messages such as `feat(tui): add mode controls` or
`chore(qemu): update image notes`. Pull requests should describe the user-facing
change, list verification commands run, mention any rootfs or QEMU artefacts
touched, and include screenshots or terminal output when TUI behaviour changes.

## Security & Configuration Tips

Do not commit expanded `rootfs/`, local virtual environments, credentials, or
machine-specific secrets. Prefer askpass or environment-based secret handling
over putting credentials in commands or documentation.
