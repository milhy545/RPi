## 2024-08-08 - [TUI Performance Optimizations]
**Learning:** Found two clear performance bottlenecks during TUI rendering loops inside `SystemMetricsMixin` in `tui.py`. The `get_local_ip` function was resolving a UDP socket connection every tick (every 2s by default). Also, `get_ram_usage` was unnecessarily parsing the entire `/proc/meminfo` file after finding its target values on the first two lines.
**Action:** Implemented a 60s class-level cache (`_cached_ip`, `_cached_ip_time`) for `get_local_ip` reducing overhead from ~0.012s to ~0.0002s per tick. Added an early exit `break` loop condition in `get_ram_usage` reducing execution time by ~40% per call. Ensure IP caching logic falls back to subclass storage (`type(self)`) for safety. Ensure file I/O early exits are used whenever possible to save CPU cycles on low-resource hardware like the Raspberry Pi.
## 2024-11-20 - [File I/O vs Subprocess Overhead]
**Learning:** Calling `asyncio.create_subprocess_shell` repeatedly for trivial commands like `grep` or `cat | wc -l` (e.g. inside periodic polling functions like `update_wifi_hotspot_info`) incurs a significant CPU and memory overhead on resource-constrained hardware like the Raspberry Pi. The event loop can get bogged down scheduling these subprocesses.
**Action:** Replace shell subprocess calls for reading files or counting lines with native Python `open()` and iteration. This eliminates subprocess overhead and avoids blocking or timeout issues with hanging shells, especially on slow SD cards or restricted CPUs.
## 2024-11-21 - [Native I/O Socket Leak Risk]
**Learning:** Replacing shell subprocess calls (like `ip -br addr`) with native Python socket and `fcntl.ioctl` calls is an excellent optimization for reducing asyncio event loop overhead on low-end hardware. However, doing this inside a periodic polling function creates a severe risk of file descriptor leaks if the socket isn't closed.
**Action:** Always explicitly close sockets (e.g., using `with contextlib.closing(socket.socket(...)) as s:`) when using them for low-level system operations to avoid crashing the application via file descriptor exhaustion.

## 2024-11-23 - [Subprocess vs Native Python shutil]
**Learning:** Found a performance bottleneck in `rpi_dashboard/services/system.py` where `subprocess.run(["df", "-h", "/"])` was used to calculate disk usage. Subprocess calls are computationally expensive, especially on a resource-constrained hardware like the Raspberry Pi, taking ~3ms per call compared to <0.1ms using native Python calls (e.g. `shutil.disk_usage`).
**Action:** Replaced the `df` subprocess call with native Python `shutil.disk_usage("/")`. Added a `_format_size` helper function to keep the API response human-readable formatting compatible with `df -h`. Always favor native Python I/O over subprocess calls where possible to avoid the CPU cost of process creation on low-end hardware.
## 2026-07-26 - Native CPU Affinity Reading
**Learning:** Querying CPU affinity can be done significantly faster (~1000x) by directly reading the `Cpus_allowed:` field in `/proc/[pid]/status` with native Python file I/O instead of spawning an expensive `taskset` subprocess, avoiding process creation overhead on resource-constrained hardware like the Raspberry Pi.
**Action:** When querying basic system or process states on low-end hardware, look for a corresponding `/proc` or `/sys` file (like `/proc/[pid]/status`) and use Python's native file I/O rather than shelling out to GNU coreutils or system binaries like `taskset`.

## 2024-05-18 - [Replacing Subprocess pgrep with Native procfs]
**Learning:** Checking for process existence using `subprocess.check_output(["pgrep", ...])` is extremely slow on resource-constrained hardware like the Raspberry Pi because it spins up a full child process. In benchmark tests, traversing `/proc/<pid>/comm` natively was ~4x faster than executing `pgrep`.
**Action:** When you need to check if a process is running (e.g. mpv, gmediarender), iterate over `/proc` directories and read `/comm` or `/cmdline` natively in Python, handling `OSError`/`IOError` safely, rather than invoking shell commands.

## 2024-11-23 - [Subprocess systemctl is-active Elimination]
**Learning:** To efficiently check if a systemd service is active natively in Python without the heavy overhead of spawning a `systemctl is-active` subprocess, check for the existence of its invocation symlink.
**Action:** Use `os.path.lexists(f'/run/systemd/units/invocation:{service_name}.service')` to avoid process creation overhead on low-end hardware.
## 2024-05-18 - [Eliminating pkill Subprocess Calls]
**Learning:** While replacing `pgrep` with native `/proc` parsing to find PIDs is a good optimization, continuing to use `subprocess.run(["kill", "-15", pid])` or `subprocess.run(["pkill", "-f", "..."])` defeats some of the purpose by still spinning up a shell process for the termination itself.
**Action:** When natively parsing the `/proc` filesystem to find a process, terminate it using native Python commands such as `os.kill(int(pid), 15)` rather than shelling out to a termination command.
## 2026-07-26 - [Subprocess vs Native Python shutil.which]
**Learning:** Spouštět celý bash proces a command jen kvůli ověření existence binárky (např. pomocí `command -v`) je na malém hardwaru zbytečně nákladné. V benchmarcích bylo nativní Pythoní `shutil.which()` přibližně 1600x rychlejší.
**Action:** Kdykoliv potřebuješ zjistit, jestli existuje nějaká utilita/binárka v systému, použij nativní `shutil.which(bin) is not None` namísto volání jakéhokoliv shell commandu.
## 2024-11-23 - [Subprocess ss ss -tln vs Native /proc/net/tcp]
**Learning:** Checking for listening ports using shell commands like `subprocess.run(["sh","-lc","ss -tln ..."])` is resource-intensive due to the overhead of spawning a shell and running `ss` and `grep`, especially on a Raspberry Pi. Reading `/proc/net/tcp` and `/proc/net/tcp6` directly is much faster and avoids process creation.
**Action:** When you need to check if a local port is listening, avoid shelling out to network utilities like `ss` or `netstat`. Instead, natively parse `/proc/net/tcp` and `/proc/net/tcp6`, matching the hex-encoded local port and connection state `0A` (TCP_LISTEN).
## 2026-09-18 - [Async terminal capture polling]
**Learning:** Replaced `subprocess.run` with `asyncio.create_subprocess_exec` in the terminal websocket polling loop to prevent blocking the event loop on every output fetch. This significantly improves WebSocket concurrency on the constrained Raspberry Pi hardware, reducing latency and making the terminal WebUI snappier.
**Action:** When handling WebSockets or recurring tasks in an asyncio loop, never use `subprocess.run` (or any synchronous I/O). Always use `asyncio.create_subprocess_exec` and await `communicate()` to avoid blocking the event loop, especially on low-core hardware like the RPi.
## 2026-09-19 - [Subprocess ps vs Native procfs parsing]
**Learning:** Checking process details by shelling out to `ps` (e.g. `ps -eo pid,ppid,args` or `ps -p [pid]`) creates significant overhead by spawning shells and processes, taking ~15ms per call. Natively iterating through `/proc` and parsing `/cmdline` and `/stat` avoids this overhead entirely, reducing execution time to <1ms.
**Action:** When you need to retrieve process details or check for specific process arguments, natively parse the `/proc` filesystem (e.g. `/proc/[pid]/cmdline` or `/proc/[pid]/stat`) instead of using `ps` subprocess calls to save significant CPU cycles and latency on low-end hardware.
## 2026-07-27 - Replace shell networking calls with native Python calls

**Learning:** Shell subprocess calls (`hostname -I`, `ip route`) are significantly slower (milliseconds) compared to native Python implementations reading `/proc` directly or using `socket` and `fcntl.ioctl` (microseconds). The performance delta in `get_network_info` was a 300x speedup. `subprocess` overhead is a well-known killer on RPi.

**Action:** Whenever fetching IPs or gateway information in a hot path or frequently called polling endpoint, directly parse `/proc/net/route`, `/proc/net/if_inet6` and use `SIOCGIFCONF` via `fcntl` to query interface IPs.
