<Implementation Plan: keys2mpv Input Device Hardening>
## Background
Currently, `keys2mpv.py` (L17) hardcodes its input device to `/dev/input/event2`. This causes failures on system reboots or when USB devices change order. There is also no way to override this via environment variables, and missing devices cause immediate silent crashes without diagnostic output. Furthermore, the media mute button uses a one-way `["set", "mute", "yes"]` command which prevents unmuting, there are no automated tests, and socket paths are somewhat inconsistent. Additionally, `rpi_dashboard/services/return_service.py` duplicates input device scanning logic (looking for Xbox controllers). This track will centralize input device discovery, harden `keys2mpv.py`, fix the mute toggle, standardize the socket path, and introduce comprehensive tests.

## Phase 1: Shared Input Discovery Module
- [ ] Task: Create new file `rpi_dashboard/services/input_devices.py` with standard imports (`import os`, `import glob`).
- [ ] Task: Implement function `def find_input_device_by_name_pattern(name_pattern: str, sysfs_base: str = "/sys/class/input") -> str | None:` in `rpi_dashboard/services/input_devices.py` that iterates over `/sys/class/input/event*/device/name`, reads the contents, and returns the corresponding `/dev/input/eventX` path if the name contains `name_pattern` (case-insensitive).
- [ ] Task: Implement function `def find_keyboard_device() -> str | None:` in `rpi_dashboard/services/input_devices.py` that checks for `/dev/input/by-id/*kbd*` symlinks using `glob.glob()`. If found, return the resolved path. If not, use `find_input_device_by_name_pattern("keyboard")`. Return `None` if nothing is found.
- [ ] Verify: `uv run python -c "from rpi_dashboard.services.input_devices import find_keyboard_device; print(find_keyboard_device())"`

## Phase 2: Refactor keys2mpv.py Device Handling & Configuration
- [ ] Task: Modify `keys2mpv.py` (around L17) to remove `INPUT_DEV = "/dev/input/event2"`.
- [ ] Task: Import `find_keyboard_device` from `rpi_dashboard.services.input_devices` in `keys2mpv.py`.
- [ ] Task: Add logic in `keys2mpv.py` main execution block to resolve the input device: `input_dev = os.environ.get("KEYS2MPV_INPUT_DEV") or find_keyboard_device()`.
- [ ] Task: Add diagnostic check in `keys2mpv.py`: if `input_dev` is `None` or path does not exist, print a descriptive error (`"ERROR: Could not find keyboard input device. Set KEYS2MPV_INPUT_DEV."`) and exit with status 1 via `sys.exit(1)`.
- [ ] Task: Modify `SOCKETS` in `keys2mpv.py` (L18) to standardize on a single priority socket by default: `SOCKETS = [os.environ.get("MPV_SOCKET", "/tmp/rpi-mpv.sock"), "/tmp/mpv-socket"]`.
- [ ] Task: Modify `KEYMAP` in `keys2mpv.py` (L27) to change the mute command from `["set", "mute", "yes"]` to `["cycle", "mute"]`.
- [ ] Verify: `uv run python keys2mpv.py --help` (or simulate running with invalid env var to see the error message)

## Phase 3: Refactor return_service.py
- [ ] Task: Modify `rpi_dashboard/services/return_service.py` to import `find_input_device_by_name_pattern` from `rpi_dashboard.services.input_devices`.
- [ ] Task: Replace the custom `/sys/class/input/event*/device/name` scanning logic in `rpi_dashboard/services/return_service.py` with a call to `find_input_device_by_name_pattern("Xbox Wireless Controller")` (or whatever the exact original pattern was).
- [ ] Verify: `uv run ruff check rpi_dashboard/services/return_service.py`

## Phase 4: Testing
- [ ] Task: Create `tests/test_keys2mpv.py`.
- [ ] Task: Write `def test_find_keyboard_device_by_id(monkeypatch):` simulating `glob.glob` returning a `/dev/input/by-id/usb-xxx-kbd` path and ensure it returns it.
- [ ] Task: Write `def test_find_keyboard_device_by_name(monkeypatch):` simulating `glob.glob` returning empty, and mocking `/sys/class/input/eventX/device/name` reads to verify `find_input_device_by_name_pattern` works.
- [ ] Task: Write `def test_keys2mpv_keymap_mute():` to import `KEYMAP` from `keys2mpv.py` and `assert KEYMAP[113] == ["cycle", "mute"]` (assuming 113 is the mute keycode based on standard linux input.h, use the actual keycode defined in L21-28).
- [ ] Verify: `uv run python -m pytest tests/test_keys2mpv.py -v`

## Acceptance Criteria
- [ ] `keys2mpv.py` resolves its input device via `KEYS2MPV_INPUT_DEV`, then `by-id/*kbd*`, then `sysfs` name pattern.
- [ ] `keys2mpv.py` gracefully exits with a helpful print statement if no device is found.
- [ ] Mute button uses `["cycle", "mute"]`.
- [ ] `rpi_dashboard/services/return_service.py` uses the shared `rpi_dashboard.services.input_devices` module.
- [ ] All existing tests pass: `uv run python -m pytest -q`
- [ ] Lint passes: `uv run ruff check .`
- [ ] `tools/verify-done.sh` passes
</Implementation Plan: keys2mpv Input Device Hardening>
