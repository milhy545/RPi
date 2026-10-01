## 2026-07-27 - [Native IP Fetch Optimization]
**Learning:** Replaced heavy `subprocess.check_output(["hostname","-I"])` with native Python socket and `fcntl.ioctl` calls for both IPv4 and IPv6 parsing during startup. This avoids high CPU cost of process creation on low-end hardware (RPi) and significantly accelerates the async event loop startup phase.
**Action:** Always prefer native python implementations over `subprocess` for system querying operations like networking and file I/O to avoid event loop stalls.

## 2026-07-27 - [Native IP Fetch Optimization]
**Learning:** Replaced heavy `subprocess.check_output(["hostname","-I"])` with native Python socket and `fcntl.ioctl` calls for both IPv4 and IPv6 parsing during startup. This avoids high CPU cost of process creation on low-end hardware (RPi) and significantly accelerates the async event loop startup phase.
**Action:** Always prefer native python implementations over `subprocess` for system querying operations like networking and file I/O to avoid event loop stalls.
