# Specification: Milhy-PC Firewall Rules

## Goal
Secure Milhy-PC by restricting inbound access to BrowserOS MCP (port 9000) and CDP (port 9108/9200) to only Tailscale interface, blocking LAN access.

## Current State
- **BrowserOS MCP:** `http://127.0.0.1:9000` on Milhy-PC (bound to 0.0.0.0:9000)
- **CDP:** Port 9108/9200 on Milhy-PC (bound to 0.0.0.0)
- **Tailscale IP:** Milhy-PC = 100.69.194.108, RPi = 100.82.217.17
- **LAN:** 192.168.0.0/24

## Requirements
1. **Allow:** Tailscale interface (100.x.x.x) → ports 9000, 9108, 9200
2. **Deny:** LAN (192.168.0.0/24) → ports 9000, 9108, 9200
3. **Allow:** Localhost (127.0.0.1) → all ports
4. **Persistent:** Rules survive reboot

## Implementation
- Use `nftables` (modern) or `iptables-legacy`
- Rules applied via systemd service or NetworkManager dispatcher
- Test from RPi (Tailscale) and from LAN device

## Acceptance Criteria
- [ ] RPi (Tailscale) can access `http://100.69.194.108:9000`
- [ ] LAN device (192.168.0.x) CANNOT access `http://192.168.0.205:9000`
- [ ] Localhost on Milhy-PC still works
- [ ] Rules persist after reboot
- [ ] No disruption to other services (Tailscale, SSH, etc.)