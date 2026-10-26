#!/usr/bin/env python3
"""
Patch Amlogic u-boot onto Armbian image.
Equivalent to:
  dd if=uboot.bin of=armbian.img conv=fsync,notrunc bs=1 count=442
  dd if=uboot.bin of=armbian.img conv=fsync,notrunc bs=512 skip=1 seek=1

This writes u-boot while preserving the MBR partition table (bytes 442-511).
"""
import sys
import os
import lzma

import glob

# Resolve paths relative to the repository root (one level up from this script's directory)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UBOOT = os.path.join(REPO_ROOT, "firmware", "uboot_HG680P-sdboot.bin")

# Dynamically find the .img.xz file in the repository root
xz_files = glob.glob(os.path.join(REPO_ROOT, "*.img.xz"))
if xz_files:
    IMG_XZ = xz_files[0]
else:
    IMG_XZ = os.path.join(REPO_ROOT, "Armbian_image.img.xz")

IMG_OUT = os.path.join(REPO_ROOT, "Armbian_patched.img")


def decompress_xz(src, dst):
    """Decompress .img.xz to .img"""
    print(f"[1/3] Decompressing {os.path.basename(src)}...")
    print("      This may take a few minutes...")
    
    with lzma.open(src, 'rb') as f_in:
        with open(dst, 'wb') as f_out:
            total = 0
            while True:
                chunk = f_in.read(1024 * 1024 * 16)  # 16MB chunks
                if not chunk:
                    break
                f_out.write(chunk)
                total += len(chunk)
                print(f"\r      Decompressed: {total / (1024*1024):.0f} MB", end="", flush=True)
    print(f"\n      Done: {dst} ({total / (1024*1024):.0f} MB)")

def patch_uboot(img_path, uboot_path):
    """Patch u-boot binary onto image, preserving MBR partition table."""
    uboot_data = open(uboot_path, 'rb').read()
    uboot_size = len(uboot_data)
    print(f"[2/3] Patching u-boot: {os.path.basename(uboot_path)} ({uboot_size} bytes)")
    
    with open(img_path, 'r+b') as img:
        # Command 1: dd if=uboot.bin of=img bs=1 count=442
        # Write first 442 bytes (before MBR partition table)
        img.seek(0)
        img.write(uboot_data[:442])
        print("      Written bytes 0-441 (bootstrap code)")
        
        # Command 2: dd if=uboot.bin of=img bs=512 skip=1 seek=1
        # Write from byte 512 onward (after MBR)
        img.seek(512)
        img.write(uboot_data[512:])
        print(f"      Written bytes 512-{uboot_size} (u-boot body)")
        
        # Verify MBR partition table preserved (bytes 442-511)
        img.seek(510)
        sig = img.read(2)
        if sig == b'\x55\xaa':
            print("      MBR signature: 55 AA ✓")
        else:
            print(f"      WARNING: MBR signature: {sig.hex()} (expected 55aa)")
        
        img.flush()
        os.fsync(img.fileno())
    
    print("      U-boot patched successfully!")

def main():
    print("=" * 60)
    print("  Armbian + U-boot Patcher for B860H/HG680P")
    print("=" * 60)
    print()
    
    # Check files exist
    if not os.path.exists(UBOOT):
        print(f"ERROR: U-boot not found: {UBOOT}")
        sys.exit(1)
    if not os.path.exists(IMG_XZ):
        print(f"ERROR: Armbian image not found: {IMG_XZ}")
        sys.exit(1)
    
    print(f"  Image:  {os.path.basename(IMG_XZ)}")
    print(f"  U-boot: {os.path.basename(UBOOT)}")
    print(f"  Output: {os.path.basename(IMG_OUT)}")
    print()
    
    # Step 1: Decompress
    if os.path.exists(IMG_OUT):
        resp = input(f"  {os.path.basename(IMG_OUT)} already exists. Overwrite? [y/N]: ")
        if resp.lower() != 'y':
            print("  Using existing decompressed image.")
        else:
            decompress_xz(IMG_XZ, IMG_OUT)
    else:
        decompress_xz(IMG_XZ, IMG_OUT)
    
    # Step 2: Patch u-boot
    patch_uboot(IMG_OUT, UBOOT)
    
    # Step 3: Done
    print()
    print("[3/3] DONE! Flash this to SD card:")
    print(f"      {IMG_OUT}")
    print()
    print("  Use balenaEtcher, Rufus, or Win32DiskImager to flash.")
    print("  Then copy aml_autoscript to the BOOT partition if needed.")
    print()

if __name__ == '__main__':
    main()
