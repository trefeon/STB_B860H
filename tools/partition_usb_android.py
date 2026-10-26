#!/usr/bin/env python3
"""
Partition the 8GB USB Flashdisk for Android TV on Amlogic B860H:
- Partition 1: 256 MB FAT32 (Label: BOOT) for kernel & bootloader scripts
- Partition 2: 2.5 GB Linux (Type: 0x83) for Android /system
- Partition 3: ~4.5 GB Linux (Type: 0x83) for Android /data
- Sector 0: Cleaned bootstrap area (no x86 code) to prevent ARM64 BootROM crash
"""

import struct
import sys
import os

# Usage: python tools/partition_usb_android.py [drive]  (default: \\.\PhysicalDrive2)
DRIVE_NAME = sys.argv[1] if len(sys.argv) > 1 else r"\\.\PhysicalDrive2"

def main():
    print(f"Opening {DRIVE_NAME} for partitioning...")
    try:
        with open(DRIVE_NAME, "r+b") as f:
            # Read current sector 0
            mbr = bytearray(f.read(512))
            
            # Disk geometry calculation
            f.seek(0, os.SEEK_END)
            total_bytes = f.tell()
            total_sectors = total_bytes // 512
            print(f"Total disk size: {total_bytes} bytes ({total_sectors} sectors, {total_bytes/1024/1024/1024:.2f} GB)")

            # Partition 1: BOOT (256 MB FAT32)
            p1_lba = 2048
            p1_sectors = 256 * 1024 * 1024 // 512  # 524,288 sectors
            p1_type = 0x0C  # FAT32 LBA

            # Partition 2: SYSTEM (2.5 GB Linux 0x83)
            p2_lba = p1_lba + p1_sectors
            p2_sectors = 2560 * 1024 * 1024 // 512 # 5,242,880 sectors
            p2_type = 0x83  # Linux

            # Partition 3: DATA (Remaining space ~4.5 GB Linux 0x83)
            p3_lba = p2_lba + p2_sectors
            p3_sectors = total_sectors - p3_lba
            p3_type = 0x83  # Linux

            print(f"P1 (BOOT):   LBA {p1_lba} to {p1_lba + p1_sectors - 1} ({p1_sectors * 512 / 1024 / 1024:.1f} MB, Type 0x{p1_type:02x})")
            print(f"P2 (SYSTEM): LBA {p2_lba} to {p2_lba + p2_sectors - 1} ({p2_sectors * 512 / 1024 / 1024:.1f} MB, Type 0x{p2_type:02x})")
            print(f"P3 (DATA):   LBA {p3_lba} to {p3_lba + p3_sectors - 1} ({p3_sectors * 512 / 1024 / 1024:.1f} MB, Type 0x{p3_type:02x})")

            # Zero out bootstrap code (bytes 0 to 445)
            for i in range(446):
                mbr[i] = 0x00

            # Helper to write partition entry
            def pack_entry(status, ptype, lba_start, num_sec):
                # Standard CHS dummy values for LBA partitions: 0xFE, 0xFF, 0xFF
                chs_start = b"\x00\x02\x00"
                chs_end = b"\xfe\xff\xff"
                return struct.pack("<B3sB3sII", status, chs_start, ptype, chs_end, lba_start, num_sec)

            mbr[446 : 462] = pack_entry(0x00, p1_type, p1_lba, p1_sectors)
            mbr[462 : 478] = pack_entry(0x00, p2_type, p2_lba, p2_sectors)
            mbr[478 : 494] = pack_entry(0x00, p3_type, p3_lba, p3_sectors)
            mbr[494 : 510] = b"\x00" * 16  # P4 empty

            # Signature
            mbr[510] = 0x55
            mbr[511] = 0xAA

            # Write back to sector 0
            f.seek(0)
            f.write(mbr)
            f.flush()
            print("Successfully written MBR partition table to sector 0!")
    except Exception as e:
        print("ERROR:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
