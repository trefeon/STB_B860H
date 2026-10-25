#!/usr/bin/env bash
# Audit Bluetooth and Wi-Fi RF state on STB
# Usage: ./check_bluetooth.sh [ssh_target] (default: stb)

set -euo pipefail

TARGET="${1:-stb}"

echo "Auditing Bluetooth and RF state on '${TARGET}'..."

ssh -o ConnectTimeout=8 "${TARGET}" bash -s << 'EOF'
set -uo pipefail

echo "=== 1. DMESG (BLUETOOTH / HCI) ==="
dmesg | grep -i -E 'blue|firmware|hci' || echo "No Bluetooth entries in dmesg (Clean)"
echo ""

echo "=== 2. RFKILL STATUS ==="
rfkill list || true
echo ""

echo "=== 3. HCICONFIG / BLUETOOTHCTL ==="
hciconfig -a 2>/dev/null || echo "No HCI controllers found"
bluetoothctl show 2>/dev/null || echo "No default bluetooth controller"
echo ""

echo "=== 4. USB DEVICES ==="
lsusb 2>/dev/null || echo "lsusb not available"
echo ""

echo "=== 5. SERIAL UART DEVICES ==="
ls -l /dev/ttyAML* /dev/ttyS* 2>/dev/null || true
echo ""

echo "=== 6. FIRMWARE FILES ==="
ls -l /lib/firmware/brcm/ /lib/firmware/rtl_bt/ 2>/dev/null || true
EOF
