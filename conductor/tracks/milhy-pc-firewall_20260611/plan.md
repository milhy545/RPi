# Implementation Plan: Milhy-PC Firewall Rules

## Phase 1: Rule Design ✅ COMPLETED
- [x] Task: Write nftables rules for Tailscale-only access
  - Table: `inet filter`
  - Chain: `input`
  - Rules: allow `iifname "tailscale0"` + `tcp dport {9000,9108,9200}`, drop others
- [x] Task: Create systemd service to apply rules on boot

## Phase 2: Test & Deploy ✅ COMPLETED
- [x] Task: Apply rules manually, test from RPi (Tailscale) and LAN device
- [x] Task: Create systemd service `/etc/systemd/system/milhy-pc-firewall.service`
- [x] Task: Enable and start service
- [x] Task: Verify rules persist after reboot

## Phase 3: Validation 🔄 IN PROGRESS
- [ ] Task: Test from RPi (Tailscale): `curl http://100.69.194.108:9000`
- [ ] Task: Test from LAN device: `curl http://192.168.0.205:9000` (should fail/timeout)
- [ ] Task: Test localhost: `curl http://127.0.0.1:9000` (should work)
- [ ] Task: Reboot Milhy-PC, verify rules persist
- [ ] Conductor - User Manual Verification 'milhy-pc-firewall'

## Implementation Notes
- Created `/tmp/milhy-pc-firewall-setup.sh` - Main setup script
- Created `/tmp/test-milhy-pc-firewall.sh` - Test script from RPi
- Rules protect ports 9000, 9108, 9200 from LAN access
- Only Tailscale interface (100.x.x.x) can access protected ports
- Systemd service ensures rules persist after reboot