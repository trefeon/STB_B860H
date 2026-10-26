#!/usr/bin/env python3
"""
Pure Python mkimage for U-Boot Script (boot.scr / autoscript).
Zero dependencies.
"""

import sys
import struct
import zlib
import time

IH_MAGIC = 0x27051956
IH_OS_LINUX = 5
IH_ARCH_ARM = 2
IH_TYPE_SCRIPT = 6
IH_COMP_NONE = 0

def make_script(input_cmd_path, output_scr_path, name="U-Boot Script"):
    with open(input_cmd_path, "rb") as f:
        data = f.read()

    data_size = len(data)
    data_crc = zlib.crc32(data) & 0xFFFFFFFF
    timestamp = int(time.time())
    name_bytes = name.encode("utf-8")[:31].ljust(32, b"\x00")

    # Header without header CRC
    header_no_crc = struct.pack(
        ">IIIIIIIBBBB32s",
        IH_MAGIC,
        0, # placeholder for hcrc
        timestamp,
        data_size,
        0, # load addr
        0, # entry point
        data_crc,
        IH_OS_LINUX,
        IH_ARCH_ARM,
        IH_TYPE_SCRIPT,
        IH_COMP_NONE,
        name_bytes
    )

    header_crc = zlib.crc32(header_no_crc) & 0xFFFFFFFF

    final_header = struct.pack(
        ">IIIIIIIBBBB32s",
        IH_MAGIC,
        header_crc,
        timestamp,
        data_size,
        0,
        0,
        data_crc,
        IH_OS_LINUX,
        IH_ARCH_ARM,
        IH_TYPE_SCRIPT,
        IH_COMP_NONE,
        name_bytes
    )

    with open(output_scr_path, "wb") as f:
        f.write(final_header + data)

    print(f"[SUCCESS] Compiled {input_cmd_path} -> {output_scr_path} ({len(final_header + data)} bytes)")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mkimage_script.py <input.cmd> <output.scr> [name]")
        sys.exit(1)
    name = sys.argv[3] if len(sys.argv) > 3 else "U-Boot Script"
    make_script(sys.argv[1], sys.argv[2], name)
