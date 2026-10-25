#!/usr/bin/env bash
# Apply system, kernel, memory, and network optimizations to STB via SSH
# Usage: ./apply_optimizations.sh [ssh_target] (default: stb)

set -euo pipefail

TARGET="${1:-stb}"

echo "============================================================"
echo " Applying optimizations to STB at '${TARGET}'..."
echo "============================================================"

ssh -o ConnectTimeout=8 "${TARGET}" bash -s << 'EOF'
set -euo pipefail

echo "1. Configuring sysctl parameters (BBR, vm.swappiness, dirty ratio, file limits)..."
sudo mkdir -p /etc/sysctl.d
sudo tee /etc/sysctl.d/99-server-opt.conf > /dev/null << 'SYSCTL_EOF'
# Memory and swap optimization
vm.swappiness = 60
vm.vfs_cache_pressure = 50
vm.dirty_background_ratio = 5
vm.dirty_ratio = 10
vm.dirty_writeback_centisecs = 6000

# Network and TCP BBR
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# File descriptor limits
fs.file-max = 2097152
SYSCTL_EOF

sudo /sbin/sysctl -p /etc/sysctl.d/99-server-opt.conf 2>/dev/null || sudo sysctl -p /etc/sysctl.d/99-server-opt.conf

echo "2. Setting CPU Governor to schedutil (or performance on demand)..."
if command -v cpufreq-set >/dev/null 2>&1; then
    sudo cpufreq-set -g schedutil 2>/dev/null || true
fi
echo schedutil | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null || true

echo "3. Disabling redundant rsyslog service (saving CPU/RAM, systemd journal handles logs)..."
sudo systemctl stop rsyslog 2>/dev/null || true
sudo systemctl disable rsyslog 2>/dev/null || true

echo "4. Capping systemd journal memory and disk usage..."
sudo mkdir -p /etc/systemd/journald.conf.d/
sudo tee /etc/systemd/journald.conf.d/00-cap-size.conf > /dev/null << 'JOURNAL_EOF'
[Journal]
SystemMaxUse=50M
RuntimeMaxUse=30M
SystemMaxFileSize=10M
MaxRetentionSec=1month
JOURNAL_EOF
sudo systemctl restart systemd-journald

echo "============================================================"
echo " Optimizations applied successfully!"
echo " Current Congestion Control: $(/sbin/sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null || sysctl -n net.ipv4.tcp_congestion_control)"
echo " Current Swappiness:         $(/sbin/sysctl -n vm.swappiness 2>/dev/null || sysctl -n vm.swappiness)"
echo " Current CPU Governor:       $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null)"
echo "============================================================"
EOF
