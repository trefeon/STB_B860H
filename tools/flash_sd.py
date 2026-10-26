import sys
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)
import os
import sys
import time
import ctypes
from ctypes import wintypes

# Disk 2 (example; verify your SD card's disk number in Disk Management first!)
# Usage: python tools/flash_sd.py [drive] [volume] [image]
#   (defaults: PhysicalDrive2, F:, Armbian_b860h.img in the current directory;
#   e.g. python tools/flash_sd.py \\.\PhysicalDrive2 \\.\F: D:\Armbian_b860h.img)
DRIVE_PATH = sys.argv[1] if len(sys.argv) > 1 else r"\\.\PhysicalDrive2"
VOLUME_PATH = sys.argv[2] if len(sys.argv) > 2 else r"\\.\F:"
IMG_PATH = sys.argv[3] if len(sys.argv) > 3 else r"Armbian_b860h.img"

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80

FSCTL_LOCK_VOLUME = 0x00090018
FSCTL_DISMOUNT_VOLUME = 0x00090020
FSCTL_UNLOCK_VOLUME = 0x0009001c
IOCTL_DISK_UPDATE_PROPERTIES = 0x00070140

kernel32 = ctypes.windll.kernel32

def flash():
    if not os.path.exists(IMG_PATH):
        print(f"Error: {IMG_PATH} not found!")
        sys.exit(1)

    img_size = os.path.getsize(IMG_PATH)
    print(f"Target Image: {IMG_PATH} ({img_size / (1024*1024):.1f} MB)")
    print(f"Target Drive: {DRIVE_PATH} (Drive F:)")

    # 1. Lock and dismount volume F:
    print("Dismounting volume F:...")
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
        print(f"Note: Could not open volume handle {VOLUME_PATH} (might already be unmounted), continuing...")

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
        print(f"Error opening {DRIVE_PATH}: Error code {err}")
        sys.exit(1)

    print(f"Successfully opened {DRIVE_PATH}! Starting raw write...")
    start_time = time.time()
    last_print = start_time
    total_written = 0
    chunk_size = 4 * 1024 * 1024  # 4 MB chunk
    buffer = ctypes.create_string_buffer(chunk_size)
    bytes_written = wintypes.DWORD()

    with open(IMG_PATH, 'rb') as f_in:
        while True:
            data = f_in.read(chunk_size)
            if not data:
                break
            # ctypes write
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
            if now - last_print >= 3:
                pct = (total_written / img_size) * 100
                speed = (total_written / (1024 * 1024)) / (now - start_time)
                print(f"Written: {total_written / (1024*1024):.1f}/{img_size / (1024*1024):.1f} MB ({pct:.1f}%) at {speed:.2f} MB/s")
                last_print = now

    print(f"\nFlushing buffers to disk...")
    kernel32.FlushFileBuffers(hDisk)
    bytesReturned = wintypes.DWORD()
    kernel32.DeviceIoControl(hDisk, IOCTL_DISK_UPDATE_PROPERTIES, None, 0, None, 0, ctypes.byref(bytesReturned), None)
    kernel32.CloseHandle(hDisk)
    if hVol != -1 and hVol != 0:
        kernel32.CloseHandle(hVol)

    elapsed = time.time() - start_time
    print(f"SUCCESS! Flashed {total_written / (1024*1024):.1f} MB in {elapsed:.1f}s ({total_written / (1024*1024) / elapsed:.2f} MB/s)")

if __name__ == "__main__":
    flash()
