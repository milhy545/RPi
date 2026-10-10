# Milhy-PC Firewall Implementation

## Overview
This document describes the implementation of firewall rules for Milhy-PC to secure RPi Dashboard services.

## Problem Statement
Milhy-PC runs critical services (BrowserOS MCP on port 9000, CDP on ports 9108/9200) that should only be accessible via Tailscale, not from the local LAN network.

## Solution
Implemented nftables firewall rules that:
1. **Allow** Tailscale interface (`tailscale0`) to access protected ports
2. **Block** LAN access to protected ports
3. **Allow** localhost access for local development
4. **Persist** rules across reboots via systemd service

## Files Created

### 1. `/tmp/milhy-pc-firewall-setup.sh`
Main setup script that:
- Backs up current firewall rules
- Creates nftables rules (with iptables fallback)
- Creates and enables systemd service
- Tests the rules

**Usage on Milhy-PC:**
```bash
# Copy script to Milhy-PC
scp /tmp/milhy-pc-firewall-setup.sh milhy-pc:/tmp/

# SSH to Milhy-PC and run
ssh milhy-pc
sudo /tmp/milhy-pc-firewall-setup.sh setup
```

### 2. `/tmp/test-milhy-pc-firewall.sh`
Test script to verify firewall rules from RPi.

**Usage from RPi:**
```bash
/tmp/test-milhy-pc-firewall.sh
```

## Firewall Rules

### nftables Rules (`/etc/nftables.conf`)
```nft
table inet filter {
    chain input {
        type filter hook input priority 0; policy accept;
        
        # Allow established/related connections
        ct state established,related accept
        
        # Allow loopback
        iif "lo" accept
        
        # Allow Tailscale interface to protected ports
        iifname "tailscale0" tcp dport {9000,9108,9200} accept
        
        # Allow SSH from Tailscale
        iifname "tailscale0" tcp dport 22 accept
        
        # Allow ICMP from anywhere
        icmp type echo-request accept
        
        # Log and drop everything else to protected ports
        tcp dport {9000,9108,9200} log prefix "FIREWALL-DROP: " drop
    }
}
```

## Testing

### Test from RPi (Tailscale)
```bash
# Should succeed
curl http://100.69.194.108:9000
curl http://100.69.194.108:9108
curl http://100.69.194.108:9200
```

### Test from LAN Device
```bash
# Should fail/timeout
curl http://192.168.0.205:9000
curl http://192.168.0.205:9108
curl http://192.168.0.205:9200
```

### Test from Milhy-PC (localhost)
```bash
# Should succeed
curl http://127.0.0.1:9000
```

## Systemd Service

### Service File (`/etc/systemd/system/milhy-pc-firewall.service`)
```ini
[Unit]
Description=Milhy-PC Firewall Rules for RPi Dashboard
After=network.target
Before=network-pre.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/nft -f /etc/nftables.conf
ExecReload=/usr/sbin/nft -f /etc/nftables.conf
ExecStop=/usr/sbin/nft flush ruleset

[Install]
WantedBy=multi-user.target
```

### Service Management
```bash
# Check status
sudo systemctl status milhy-pc-firewall

# Restart service
sudo systemctl restart milhy-pc-firewall

# Stop service (emergency only)
sudo systemctl stop milhy-pc-firewall

# View logs
sudo journalctl -u milhy-pc-firewall
```

## Rollback

If issues occur, restore backup:
```bash
# List backups
ls -la /tmp/nft-backup-*.rules

# Restore specific backup
sudo nft -f /tmp/nft-backup-YYYYMMDD-HHMMSS.rules
```

## Acceptance Criteria

- [ ] RPi (Tailscale) can access `http://100.69.194.108:9000`
- [ ] LAN device (192.168.0.x) CANNOT access `http://192.168.0.205:9000`
- [ ] Localhost on Milhy-PC still works
- [ ] Rules persist after reboot
- [ ] No disruption to other services (Tailscale, SSH, etc.)

## Next Steps

1. **Manual Verification**: Run setup script on Milhy-PC
2. **Test from RPi**: Run test script to verify rules
3. **Test from LAN**: Verify LAN access is blocked
4. **Reboot Test**: Verify rules persist after reboot
5. **Update Plan**: Mark tasks as completed in conductor