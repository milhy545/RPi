import timeit
from typing import List

# Generate a realistic dummy output from bluetoothctl
# e.g., "Device 00:11:22:33:44:55 My Speaker"
dummy_output = "\n".join([f"Device {i:02x}:11:22:33:44:55 Test Device {i}" for i in range(100)]) + "\n\n" + "\n".join([f"Device FF:EE:DD:CC:BB:{i:02x} Another Device {i}" for i in range(50)])

def original_update_bt() -> List[str]:
    results = []
    if dummy_output:
        for line in dummy_output.split("\n"):
            if line.strip():
                # Note: this matches the requested format we are migrating to
                parts = line.split(" ", 2)
                if len(parts) >= 3:
                    results.append(f"{parts[2]} ({parts[1]})")
    return results

def optimized_update_bt() -> List[str]:
    if not dummy_output:
        return []
    # Avoid .strip() and use comprehension
    return [
        f"{p[2]} ({p[1]})"
        for line in dummy_output.split("\n")
        if line and len(p := line.split(" ", 2)) == 3
    ]

def original_handle_get_devices() -> List[str]:
    return [line.strip() for line in dummy_output.split("\n") if line.strip()]

def optimized_handle_get_devices() -> List[str]:
    # Bluetooth lines don't have leading/trailing spaces normally
    return [line for line in dummy_output.split("\n") if line]

if __name__ == "__main__":
    n = 10000
    print("--- Benchmark Results ---\n")

    # 1. update_bluetooth_devices
    orig_time_1 = timeit.timeit(original_update_bt, number=n)
    print(f"Original update_bluetooth_devices: {orig_time_1:.6f} s")
    opt_time_1 = timeit.timeit(optimized_update_bt, number=n)
    print(f"Optimized update_bluetooth_devices: {opt_time_1:.6f} s")
    print(f"Improvement: {((orig_time_1 - opt_time_1) / orig_time_1) * 100:.2f}%\n")

    # 2. handle_bluetooth_get_devices
    orig_time_2 = timeit.timeit(original_handle_get_devices, number=n)
    print(f"Original handle_bluetooth_get_devices: {orig_time_2:.6f} s")
    opt_time_2 = timeit.timeit(optimized_handle_get_devices, number=n)
    print(f"Optimized handle_bluetooth_get_devices: {opt_time_2:.6f} s")
    print(f"Improvement: {((orig_time_2 - opt_time_2) / orig_time_2) * 100:.2f}%\n")
