#!/usr/bin/env python3
r"""
Write custom Android system.img directly to Partition 2 of Kingston 8GB USB Flashdisk via Win32 API.
Target: \\.\PhysicalDrive2 at sector offset 526,336 (269,484,032 bytes).
"""

import sys
import os
import time
import ctypes
from ctypes import wintypes

# Usage: python tools/flash_android_p2.py [drive] [volume] [image]  (defaults below;
#   verify the disk number in Disk Management first, e.g. image D:\custom_rom_build\custom_system.img)
DRIVE_PATH = sys.argv[1] if len(sys.argv) > 1 else r"\\.\PhysicalDrive2"
VOLUME_PATH = sys.argv[2] if len(sys.argv) > 2 else r"\\.\F:"
IMG_PATH = sys.argv[3] if len(sys.argv) > 3 else r"custom_system.img"
PART2_LBA = 526336

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FSCTL_LOCK_VOLUME = 0x00090018
FSCTL_DISMOUNT_VOLUME = 0x00090020
IOCTL_DISK_UPDATE_PROPERTIES = 0x00070140
FILE_BEGIN = 0

kernel32 = ctypes.windll.kernel32

def flash_p2():
    if not os.path.exists(IMG_PATH):
        print(f"ERROR: Image file not found: {IMG_PATH}")
        sys.exit(1)

    img_size = os.path.getsize(IMG_PATH)
    start_offset = PART2_LBA * 512
    print(f"=== Writing Custom Android System Image to USB Flashdisk ===")
    print(f"Source: {IMG_PATH} ({img_size/1024/1024:.1f} MB)")
    print(f"Destination: {DRIVE_PATH} at Partition 2 (Offset: {start_offset} bytes)")

    # 1. Lock and dismount Volume F:
    print(f"Attempting to lock and dismount {VOLUME_PATH}...")
    hVol = kernel32.CreateFileW(
        VOLUME_PATH,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        0,
        None
    )

    if hVol != -1 and hVol != 0:
        bytesReturned = wintypes.DWORD()
        kernel32.DeviceIoControl(hVol, FSCTL_LOCK_VOLUME, None, 0, None, 0, ctypes.byref(bytesReturned), None)
        kernel32.DeviceIoControl(hVol, FSCTL_DISMOUNT_VOLUME, None, 0, None, 0, ctypes.byref(bytesReturned), None)
        print("Volume F: locked and dismounted.")
    else:
        print(f"Note: Could not open volume handle {VOLUME_PATH}, continuing...")

    # 2. Open PhysicalDrive2
    print(f"Opening {DRIVE_PATH} for writing...")
    hDisk = kernel32.CreateFileW(
        DRIVE_PATH,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        0,
        None
    )

    if hDisk == -1 or hDisk == 0:
        err = kernel32.GetLastError()
        print(f"Error opening {DRIVE_PATH}: Error code {err} (Run as Administrator!)")
        sys.exit(1)

    # 3. Seek to Partition 2 offset
    new_pos = ctypes.c_longlong()
    seek_success = kernel32.SetFilePointerEx(
        hDisk,
        ctypes.c_longlong(start_offset),
        ctypes.byref(new_pos),
        FILE_BEGIN
    )

    if not seek_success:
        err = kernel32.GetLastError()
        print(f"SetFilePointerEx failed: error {err}")
        kernel32.CloseHandle(hDisk)
        sys.exit(1)

    print(f"Successfully seeked to offset {new_pos.value}! Starting write...")
    start_time = time.time()
    last_print = start_time
    total_written = 0
    chunk_size = 4 * 1024 * 1024  # 4 MB
    buffer = ctypes.create_string_buffer(chunk_size)
    bytes_written = wintypes.DWORD()

    with open(IMG_PATH, 'rb') as f_in:
        while True:
            data = f_in.read(chunk_size)
            if not data:
                break
            ctypes.memmove(buffer, data, len(data))
            success = kernel32.WriteFile(
                hDisk,
                buffer,
                len(data),
                ctypes.byref(bytes_written),
                None
            )
            if not success:
                err = kernel32.GetLastError()
                print(f"\nWriteFile failed at offset {total_written}: error {err}")
                kernel32.CloseHandle(hDisk)
                sys.exit(1)

            total_written += bytes_written.value
            now = time.time()
            if now - last_print >= 2.0:
                pct = (total_written / img_size) * 100
                speed = (total_written / (1024 * 1024)) / (now - start_time)
                print(f"  Written: {total_written / (1024*1024):.1f}/{img_size / (1024*1024):.1f} MB ({pct:.1f}%) at {speed:.1f} MB/s")
                last_print = now

    print(f"\nFlushing buffers to disk...")
    kernel32.FlushFileBuffers(hDisk)
    bytesReturned = wintypes.DWORD()
    kernel32.DeviceIoControl(hDisk, IOCTL_DISK_UPDATE_PROPERTIES, None, 0, None, 0, ctypes.byref(bytesReturned), None)
    kernel32.CloseHandle(hDisk)
    if hVol != -1 and hVol != 0:
        kernel32.CloseHandle(hVol)

    elapsed = time.time() - start_time
    print(f"[SUCCESS] Flashed Partition 2: {total_written / (1024*1024):.1f} MB in {elapsed:.1f}s ({total_written / (1024*1024) / elapsed:.1f} MB/s)")

if __name__ == "__main__":
    flash_p2()
