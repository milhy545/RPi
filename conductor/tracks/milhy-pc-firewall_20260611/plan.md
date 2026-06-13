# Implementation Plan: Milhy-PC Firewall Rules

## Phase 1: Rule Design
- [ ] Task: Write nftables rules for Tailscale-only access
  - Table: `inet filter`
  - Chain: `input`
  - Rules: allow `iifname "tailscale0"` + `tcp dport {9000,9108,9200}`, drop others
- [ ] Task: Create systemd service to apply rules on boot

## Phase 2: Test & Deploy
- [ ] Task: Apply rules manually, test from RPi (Tailscale) and LAN device
- [ ] Task: Create systemd service `/etc/systemd/system/milhy-pc-firewall.service`
- [ ] Task: Enable and start service
- [ ] Task: Verify rules persist after reboot

## Phase 3: Validation
- [ ] Task: Test from RPi (Tailscale): `curl http://100.69.194.108:9000`
- [ ] Task: Test from LAN device: `curl http://192.168.0.205:9000` (should fail/timeout)
- [ ] Task: Test localhost: `curl http://127.0.0.1:9000` (should work)
- [ ] Task: Reboot Milhy-PC, verify rules persist
- [ ] Conductor - User Manual Verification 'milhy-pc-firewall'