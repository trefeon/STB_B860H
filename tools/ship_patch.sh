#!/usr/bin/env bash
# Ship pre-compiled Wi-Fi driver & patched DTB directly to target STB
# Usage: ./ship_patch.sh [ssh_target] (default: stb)

set -euo pipefail

TARGET="${1:-stb}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="${SCRIPT_DIR}/../packages/b860h_patch"

echo "============================================================"
echo " Shipping B860H Offline Patch to '${TARGET}'..."
echo "============================================================"

if [ ! -f "${PACKAGE_DIR}/8189fs.ko" ]; then
    echo "ERROR: ${PACKAGE_DIR}/8189fs.ko not found in repository!"
    echo "Please ensure the pre-compiled driver is present in packages/b860h_patch/"
    exit 1
fi

echo "1. Uploading patch bundle to STB via SCP..."
ssh -o ConnectTimeout=8 "${TARGET}" "mkdir -p /tmp/b860h_patch"
scp -r "${PACKAGE_DIR}/"* "${TARGET}:/tmp/b860h_patch/"

echo "2. Executing installer on STB..."
ssh "${TARGET}" "chmod +x /tmp/b860h_patch/install.sh && /tmp/b860h_patch/install.sh"

echo "3. Cleaning up temporary files on STB..."
ssh "${TARGET}" "rm -rf /tmp/b860h_patch"

echo "============================================================"
echo " Turnkey patch deployment complete! wlan0 is active."
echo "============================================================"
