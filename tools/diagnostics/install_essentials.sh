#!/usr/bin/env bash
# Install essential server tools, update packages, and clean caches
# Usage: ./install_essentials.sh [ssh_target] (default: stb)

set -euo pipefail

TARGET="${1:-stb}"

echo "Connecting to '${TARGET}' to update system and install essential packages..."

ssh -o ConnectTimeout=8 "${TARGET}" bash -s << 'EOF'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

PACKAGES=(
    htop tmux curl wget git rsync
    unzip zip dnsutils net-tools ncdu
    build-essential lm-sensors usbutils pciutils
)

echo "1. Updating APT package lists..."
sudo apt-get update -y

echo "2. Upgrading installed packages..."
sudo apt-get upgrade -y

echo "3. Installing essential packages: ${PACKAGES[*]}..."
sudo apt-get install -y "${PACKAGES[@]}"

echo "4. Cleaning up package caches..."
sudo apt-get autoremove -y --purge
sudo apt-get autoclean -y
sudo apt-get clean -y

echo "Server setup and package installation complete!"
EOF
