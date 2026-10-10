import glob
import os
from pathlib import Path


def find_all_input_devices_by_name_pattern(
    name_pattern: str, sysfs_base: str = "/sys/class/input"
) -> list[str]:
    """Iterate over sysfs input devices and match name against pattern (case-insensitive). Return all matches."""
    pattern = name_pattern.lower()
    matches = []
    for sys_path in sorted(glob.glob(os.path.join(sysfs_base, "event*"))):
        name_file = os.path.join(sys_path, "device", "name")
        if os.path.isfile(name_file):
            try:
                with open(name_file, "r", encoding="utf-8", errors="ignore") as f:
                    name = f.read().strip().lower()
                    if pattern in name:
                        dev_name = os.path.basename(sys_path)
                        dev_path = os.path.join("/dev", "input", dev_name)
                        if os.path.exists(dev_path):
                            matches.append(dev_path)
            except OSError:
                continue
    return matches


def find_input_device_by_name_pattern(
    name_pattern: str, sysfs_base: str = "/sys/class/input"
) -> str | None:
    """Iterate over sysfs input devices and match name against pattern (case-insensitive). Return first match."""
    matches = find_all_input_devices_by_name_pattern(name_pattern, sysfs_base)
    return matches[0] if matches else None


def find_keyboard_device() -> str | None:
    """Find keyboard input device via /dev/input/by-id symlinks, fallback to sysfs scanning."""
    by_id_kbds = sorted(glob.glob("/dev/input/by-id/*kbd*"))
    for kbd in by_id_kbds:
        resolved = str(Path(kbd).resolve())
        if os.path.exists(resolved):
            return resolved

    # Fallback to sysfs search
    return find_input_device_by_name_pattern("keyboard")
