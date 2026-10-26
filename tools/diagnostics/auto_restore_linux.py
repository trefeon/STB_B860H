#!/usr/bin/env python3
"""
Auto-catch U-Boot on <COM-PORT> (e.g. COM5 on Windows), boot clean Linux
Armbian, and restore backup. Port comes from argv[1] or STB_COM_PORT.
"""

import sys
import os
import time
import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("STB_COM_PORT", "<COM-PORT>")
BAUD = 115200

def main():
    if PORT == "<COM-PORT>":
        print("ERROR: no serial port given. Pass it as argv[1] (e.g. COM5 on Windows) or set STB_COM_PORT.")
        sys.exit(1)
    print(f"Connecting to {PORT} at {BAUD} baud...")
    ser = serial.Serial(PORT, BAUD, timeout=0.05)
    print("Waiting for STB power cycle (flip power switch OFF then ON)...")

    buf = ""
    in_uboot = False

    while True:
        raw = ser.read(ser.in_waiting or 1)
        if raw:
            text = raw.decode("latin-1", errors="ignore")
            sys.stdout.write(text)
            sys.stdout.flush()
            buf += text

            # Catch autoboot
            if any(k in buf.lower() for k in ["hit enter", "autoboot", "stop autoboot"]):
                print("\n[ACTION] Detected autoboot! Stopping...")
                for _ in range(8):
                    ser.write(b" \n")
                    time.sleep(0.05)
                buf = ""
                time.sleep(0.3)

            # Inside U-Boot prompt
            if any(buf.strip().endswith(p) for p in ["#", "gxl_p212_v1#"]) and not in_uboot:
                print("\n[SUCCESS] Inside U-Boot prompt! Executing clean Armbian boot...")
                in_uboot = True
                time.sleep(0.3)

                boot_cmds = [
                    "setenv dtb_addr 0x1000000",
                    "setenv env_addr 0x1040000",
                    "setenv kernel_addr 0x11000000",
                    "setenv initrd_addr 0x15000000",
                    "setenv boot_start booti ${kernel_addr} ${initrd_addr} ${dtb_addr}",
                    "setenv addmac 'if printenv mac; then setenv bootargs ${bootargs} mac=${mac}; elif printenv eth_mac; then setenv bootargs ${bootargs} mac=${eth_mac}; elif printenv ethaddr; then setenv bootargs ${bootargs} mac=${ethaddr}; fi'",
                    "fatload mmc 1:1 0x1040000 uEnv.txt",
                    "env import -t 0x1040000 ${filesize}",
                    "setenv bootargs ${APPEND}",
                    "fatload mmc 1:1 ${kernel_addr} ${LINUX}",
                    "fatload mmc 1:1 ${initrd_addr} ${INITRD}",
                    "fatload mmc 1:1 ${dtb_addr} ${FDT}",
                    "run addmac",
                    "run boot_start"
                ]

                for cmd in boot_cmds:
                    print(f"\n[EXEC]: {cmd}")
                    ser.write(f"{cmd}\n".encode())
                    t0 = time.time()
                    while time.time() - t0 < 1.2:
                        r = ser.read(ser.in_waiting or 1)
                        if r:
                            sys.stdout.write(r.decode("latin-1", errors="ignore"))
                            sys.stdout.flush()
                        time.sleep(0.02)
                break
        time.sleep(0.01)

    ser.close()
    print("\nLinux boot command sent.")

if __name__ == "__main__":
    main()
