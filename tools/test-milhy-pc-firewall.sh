#!/usr/bin/env bash
# Automated verification script for Milhy-PC firewall

set -euo pipefail

MILHY_PC_LAN="192.168.0.67"
PORTS=(9000 9108 9200)

echo "=== Milhy-PC Firewall Validation ==="

# 1. Discover Milhy-PC Tailscale IP
MILHY_PC_TS=$(tailscale status | grep "Milhy-PC" | awk '{print $1}' || echo "100.108.125.109")
echo "Milhy-PC LAN IP: $MILHY_PC_LAN"
echo "Milhy-PC Tailscale IP: $MILHY_PC_TS"

PASS=0
FAIL=0

# Helper function to check connection
check_port() {
    local host="$1"
    local port="$2"
    local expected="$3" # "allow" or "block"

    if nc -z -w 3 "$host" "$port" 2>/dev/null; then
        if [ "$expected" = "allow" ]; then
            echo "  [PASS] $host:$port is ACCESSIBLE (as expected)"
            PASS=$((PASS + 1))
        else
            echo "  [FAIL] $host:$port is ACCESSIBLE (should be blocked!)"
            FAIL=$((FAIL + 1))
        fi
    else
        if [ "$expected" = "block" ]; then
            echo "  [PASS] $host:$port is BLOCKED (as expected)"
            PASS=$((PASS + 1))
        else
            echo "  [FAIL] $host:$port is BLOCKED (should be accessible!)"
            FAIL=$((FAIL + 1))
        fi
    fi
}

echo ""
echo "--- Testing LAN Access ($MILHY_PC_LAN) - Should be BLOCKED ---"
for port in "${PORTS[@]}"; do
    check_port "$MILHY_PC_LAN" "$port" "block"
done

echo ""
echo "--- Testing Tailscale Access ($MILHY_PC_TS) - Should be ALLOWED ---"
for port in "${PORTS[@]}"; do
    check_port "$MILHY_PC_TS" "$port" "allow"
done

echo ""
echo "Summary: $PASS Passed, $FAIL Failed"

if [ "$FAIL" -gt 0 ]; then
    echo "Firewall validation FAILED!"
    exit 1
else
    echo "Firewall validation PASSED!"
    exit 0
fi
