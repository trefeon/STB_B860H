#!/usr/bin/env bash
# Trigger STB reboot and wait for it to return online
# Usage: ./reboot_and_check.sh [ssh_target] (default: stb)

set -euo pipefail

TARGET="${1:-stb}"

echo "Connecting to '${TARGET}' to initiate reboot..."
ssh -o ConnectTimeout=5 "${TARGET}" "sudo reboot" || true

echo "Reboot command dispatched. Waiting for STB to shut down and boot back up..."
sleep 12

MAX_ATTEMPTS=25
ATTEMPT=1
ONLINE=false

while [ "$ATTEMPT" -le "$MAX_ATTEMPTS" ]; do
    echo "Probing connection (attempt ${ATTEMPT}/${MAX_ATTEMPTS})..."
    if ssh -o ConnectTimeout=3 -o BatchMode=yes "${TARGET}" "uptime" 2>/dev/null; then
        ONLINE=true
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    sleep 3
done

if [ "$ONLINE" = false ]; then
    echo "ERROR: STB did not return online within timeout window."
    exit 1
fi

echo ""
echo "============================================================"
echo " STB is back online! Verifying post-reboot health..."
echo "============================================================"
ssh "${TARGET}" bash -s << 'EOF'
echo "Uptime: $(uptime)"
echo "Governor: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || true)"
echo "Mounts: $(mount | grep ' / ')"
echo "Memory: $(free -h)"
echo "Recent errors: $(dmesg | grep -i -E 'error|fail|warn' | tail -n 5 || true)"
EOF
