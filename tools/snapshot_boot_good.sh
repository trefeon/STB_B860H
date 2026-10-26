#!/bin/bash
# Promote the RUNNING /boot set to the .good fallback slot.
# Run BEFORE any kernel update, and after any verified-good boot.
# The U-Boot fallback block boots this set when the primary fails.
set -e
cd /
sudo cp -f /boot/zImage /boot/zImage.good
sudo cp -f /boot/uInitrd /boot/uInitrd.good
sudo cp -f /boot/dtb/amlogic/meson-gxl-s905x-b860h.dtb /boot/dtb/amlogic/meson-gxl-s905x-b860h.dtb.good
uname -r | sudo tee /boot/.expected_kernel > /dev/null
echo "--- .good slot ---"
ls -la /boot/zImage.good /boot/uInitrd.good /boot/dtb/amlogic/meson-gxl-s905x-b860h.dtb.good
echo "expected: $(cat /boot/.expected_kernel)"
