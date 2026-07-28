## Background
Phase 1 (Rule Design) and Phase 2 (Test & Deploy) are COMPLETED. nftables rules were created for Tailscale-only access and the systemd service was enabled on Milhy-PC. Phase 3 (Validation) is IN PROGRESS. We need an automated validation script at `tools/test-milhy-pc-firewall.sh` to verify that the firewall correctly allows Tailscale access to ports 9000, 9108, and 9200 on Milhy-PC, while blocking LAN access (192.168.0.67). This protects BrowserOS MCP and CDP.

## Phase 1: Create Validation Script
- [ ] Task: Create a bash script at `tools/test-milhy-pc-firewall.sh`. The script must discover Milhy-PC's Tailscale IP (via `tailscale status`), test Tailscale access to ports 9000, 9108, 9200 (should succeed), test LAN access to `192.168.0.67` on the same ports with a 3s timeout (should fail), and SSH into Milhy-PC to test localhost access to the same ports (should succeed). The script must output clear PASS/FAIL for each check and exit with a non-zero code if any check fails.
- [ ] Task: Make the script executable by running `chmod +x tools/test-milhy-pc-firewall.sh`.
- [ ] Verify: `ls -la tools/test-milhy-pc-firewall.sh`

## Phase 2: Run Validation & Finalize
- [ ] Task: Run `./tools/test-milhy-pc-firewall.sh` from the RPi to verify the current firewall state on Milhy-PC.
- [ ] Task: Manually reboot Milhy-PC, then re-run `./tools/test-milhy-pc-firewall.sh` to verify that the firewall rules persist across reboots.
- [ ] Verify: `./tools/test-milhy-pc-firewall.sh`

## Acceptance Criteria
- [ ] Script successfully validates Tailscale access to ports 9000, 9108, 9200 on Milhy-PC.
- [ ] Script successfully validates LAN access is blocked (timeouts within 3s).
- [ ] Script successfully validates localhost access on Milhy-PC works.
- [ ] Firewall rules persist after reboot.
- [ ] All existing tests pass: `uv run python -m pytest -q`
- [ ] Lint passes: `uv run ruff check .`
- [ ] `tools/verify-done.sh` passes