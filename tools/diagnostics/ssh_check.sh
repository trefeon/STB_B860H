#!/usr/bin/env bash
# Quick remote health check for ZTE B860H running Armbian
# Usage: ./ssh_check.sh [ssh_target] (default: stb)

set -euo pipefail

TARGET="${1:-stb}"

echo "============================================================"
echo " Connecting to STB at '${TARGET}'..."
echo "============================================================"

ssh -o ConnectTimeout=8 "${TARGET}" bash -s << 'EOF'
set -uo pipefail

cyan='\033[0;36m'
green='\033[0;32m'
nc='\033[0m'

run_section() {
    local title="$1"
    local cmd="$2"
    echo -e "${cyan}============================================================${nc}"
    echo -e "${green}  ${title}${nc}"
    echo -e "${cyan}============================================================${nc}"
    echo "Running: ${cmd}"
    echo "------------------------------------------------------------"
    eval "${cmd}" 2>&1 || true
    echo ""
}

run_section "System & Kernel" "uname -a"
run_section "Uptime & Load" "uptime"
run_section "CPU Temperature" 'echo "$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || echo 0) / 1000" | bc -l 2>/dev/null || cat /sys/class/thermal/thermal_zone0/temp'
run_section "Memory & Swap Usage" "free -h && /sbin/swapon --show 2>/dev/null || true"
run_section "Disk & Storage Partitions" "df -h / /boot /mnt/storage 2>/dev/null || df -h"
run_section "Block Devices Layout" "lsblk -o NAME,SIZE,TYPE,MOUNTPOINTS,LABEL"
run_section "Network Interfaces" "ip -br addr show"
run_section "Routing & Failover Metrics" "ip route show | grep default || true"
run_section "Wi-Fi Connection Status" "nmcli device status 2>/dev/null || true"
run_section "Wi-Fi Modules loaded" "lsmod | grep -E 'brcm|rtl|mt76|cfg80211|mac80211' | head -n 10 || true"
run_section "Failed Services" "systemctl --failed --no-legend 2>/dev/null || true"
run_section "Recent Kernel Errors/Warnings" "dmesg | grep -i -E 'error|fail|warn' | tail -n 15 || true"

echo "Health check completed."
EOF
