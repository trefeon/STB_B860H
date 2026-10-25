#!/usr/bin/env bash
# Audit active performance optimizations on STB
# Usage: ./check_optimizations.sh [ssh_target] (default: stb)

set -euo pipefail

TARGET="${1:-stb}"

echo "Connecting to '${TARGET}' to inspect system optimizations..."

ssh -o ConnectTimeout=8 "${TARGET}" bash -s << 'EOF'
set -uo pipefail

echo "=== 1. FSTAB MOUNTS ==="
cat /etc/fstab
echo ""

echo "=== 2. CPU GOVERNORS & FREQUENCY ==="
echo "Governors: $(cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null | tr '\n' ' ')"
echo "Current Freq: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null) kHz"
echo ""

echo "=== 3. ZRAM & SWAP STATUS ==="
/sbin/zramctl 2>/dev/null || /usr/sbin/zramctl 2>/dev/null || echo "No zramctl available"
/sbin/swapon --show 2>/dev/null || true
echo ""

echo "=== 4. SYSCTL TUNING ==="
/sbin/sysctl vm.swappiness vm.dirty_ratio net.ipv4.tcp_congestion_control 2>/dev/null || true
echo ""

echo "=== 5. SYSTEMD JOURNALD LIMITS ==="
cat /etc/systemd/journald.conf.d/00-cap-size.conf 2>/dev/null || echo "Default journal limits"
echo ""

echo "=== 6. ACTIVE SYSTEM SERVICES ==="
systemctl list-units --type=service --state=running --no-legend 2>/dev/null | awk '{print $1, $2, $3}' | head -n 20
echo ""

echo "=== 7. BLUETOOTH / HCIUART STATUS ==="
systemctl status bluetooth 2>/dev/null || systemctl status hciuart 2>/dev/null || echo "Bluetooth service inactive (clean)"
EOF
