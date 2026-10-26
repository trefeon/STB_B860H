#!/bin/bash
# Resolve script's directory and move to repo root
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/.."
UBOOT="firmware/uboot_HG680P-sdboot.bin"
IMG="Armbian_patched.img"

echo "=== U-boot: $UBOOT ==="
ls -l "$UBOOT"

echo ""
echo "=== dd #1: first 442 bytes (preserve MBR partition table) ==="
dd if="$UBOOT" of="$IMG" conv=fsync,notrunc bs=1 count=442

echo ""
echo "=== dd #2: sector 1 onward ==="
dd if="$UBOOT" of="$IMG" conv=fsync,notrunc bs=512 skip=1 seek=1

echo ""
echo "=== Verify MBR signature ==="
dd if="$IMG" bs=1 skip=510 count=2 2>/dev/null | xxd

echo ""
echo "=== DONE! Flash Armbian_patched.img to SD card ==="
ls -lh "$IMG"
