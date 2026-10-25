#!/bin/bash
# ==============================================================================
# Auto-Patch Script for ZTE ZXV10 B860H (Amlogic S905X) on Armbian Linux 6.x
# Target: Realtek RTL8189FS Wi-Fi Driver Build & Bluetooth DTB Clean Patch
# ==============================================================================
set -e

if [ "$(id -u)" != "0" ]; then
    echo "[-] Error: This script must be run as root (e.g. sudo bash $0)"
    exit 1
fi

KERNEL_VER=$(uname -r)
echo "=========================================================="
echo "  B860H Wi-Fi (RTL8189FS) & Bluetooth Auto-Patch Tool"
echo "  Kernel Version: ${KERNEL_VER}"
echo "=========================================================="

# 1. Install Dependencies
echo "[1/6] Installing build dependencies..."
apt-get update -y
apt-get install -y --no-install-recommends build-essential git wget device-tree-compiler bc

# 2. Setup Kernel Headers
echo "[2/6] Checking kernel build headers..."
if [ ! -d "/lib/modules/${KERNEL_VER}/build" ]; then
    echo "[*] Kernel headers not found for ${KERNEL_VER}. Downloading from Ophub releases..."
    cd /tmp
    rm -rf deb-${KERNEL_VER}*
    wget -q --show-progress "https://github.com/ophub/kernel/releases/download/kernel_stable/deb-${KERNEL_VER}.tar.gz" || \
        wget -q --show-progress "https://github.com/ophub/kernel/releases/download/kernel_stable/deb-6.12.112.tar.gz"
    tar -xzf deb-*.tar.gz
    dpkg -i --force-depends deb-*/linux-headers_*.deb
fi

# 3. Patch Kernel Headers Makefile & Native Modpost
echo "[3/6] Patching kernel headers for host GCC & compiling native modpost..."
KSRC="/lib/modules/${KERNEL_VER}/build"
# Fix GCC 12/13 alignment flag compatibility
if grep -q "\-fmin-function-alignment=" "${KSRC}/Makefile" 2>/dev/null; then
    sed -i 's/-fmin-function-alignment=/-falign-functions=/g' "${KSRC}/Makefile"
fi

# Recompile modpost natively for host libc
cd "${KSRC}"
if [ -f "scripts/mod/modpost.c" ]; then
    gcc -O2 -Iscripts/include -o scripts/mod/modpost scripts/mod/modpost.c scripts/mod/file2alias.c scripts/mod/sumversion.c scripts/mod/symsearch.c 2>/dev/null || true
fi

# 4. Clone and Patch RTL8189FS Driver
echo "[4/6] Fetching and patching RTL8189FS driver source..."
cd /tmp
rm -rf rtl8189fs-armbian
git clone --depth 1 https://github.com/gustiarto/rtl8189fs-armbian.git
cd rtl8189fs-armbian

# Patch Linux 6.12+ set_monitor_channel netdev argument
if grep -q "KERNEL_VERSION(6, 13, 0)" os_dep/linux/ioctl_cfg80211.c; then
    echo "[*] Applying Linux 6.12+ cfg80211 API compatibility patch..."
    sed -i 's/KERNEL_VERSION(6, 13, 0)/KERNEL_VERSION(6, 12, 0)/g' os_dep/linux/ioctl_cfg80211.c
fi

# 5. Compile and Install Module
echo "[5/6] Compiling 8189fs.ko on all CPU cores..."
make clean >/dev/null 2>&1 || true
make -j$(nproc) ARCH=arm64 KSRC="${KSRC}"

TARGET_DIR="/lib/modules/${KERNEL_VER}/kernel/drivers/net/wireless/realtek/rtl8189fs"
mkdir -p "${TARGET_DIR}"
cp -f 8189fs.ko "${TARGET_DIR}/"
depmod -a

if ! grep -q "8189fs" /etc/modules 2>/dev/null; then
    echo "8189fs" >> /etc/modules
fi
modprobe 8189fs

# 6. Patch Device Tree to Disable Phantom Broadcom Bluetooth Timeout
echo "[6/6] Patching Device Tree (disabling ghost Broadcom Bluetooth)..."
DTB_FILE=$(grep "FDT=" /boot/uEnv.txt 2>/dev/null | cut -d'=' -f2)
if [ -z "${DTB_FILE}" ]; then
    DTB_FILE="/dtb/amlogic/meson-gxl-s905x-b860h.dtb"
fi

FULL_DTB="/boot${DTB_FILE}"
if [ -f "${FULL_DTB}" ]; then
    echo "[*] Decompiling ${FULL_DTB}..."
    dtc -I dtb -O dts -o /tmp/target.dts "${FULL_DTB}" 2>/dev/null
    if grep -q "compatible = \"brcm,bcm43438-bt\";" /tmp/target.dts && ! grep -q "status = \"disabled\";" /tmp/target.dts; then
        echo "[*] Disabling Broadcom BT node in DTS..."
        sed -i '/compatible = "brcm,bcm43438-bt";/a \t\t\t\t\tstatus = "disabled";' /tmp/target.dts
        cp -f "${FULL_DTB}" "${FULL_DTB}.bak"
        dtc -I dts -O dtb -o "${FULL_DTB}" /tmp/target.dts 2>/dev/null
        echo "[✓] Device tree updated successfully!"
    fi
fi

echo "=========================================================="
echo "  [✓] Auto-Patch Completed Successfully!"
echo "  - Wi-Fi Driver: 8189fs loaded into kernel"
echo "  - Bluetooth: Phantom Broadcom UART timeout eliminated"
echo "  Run 'ip link show wlan0' or 'nmcli dev wifi list' to test."
echo "=========================================================="
