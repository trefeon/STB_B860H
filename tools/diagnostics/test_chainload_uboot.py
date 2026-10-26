#!/usr/bin/env python3
"""
Test U-Boot Chainloading via <COM-PORT> (e.g. COM5 on Windows).
Loads u-boot.ext from USB flashdisk into RAM at 0x1000000 and executes 'go 0x1000000'.
"""

import sys
import os
import time
import subprocess
import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("STB_COM_PORT", "<COM-PORT>")
BAUD = 115200

def main():
    if PORT == "<COM-PORT>":
        print("ERROR: no serial port given. Pass it as argv[1] (e.g. COM5 on Windows) or set STB_COM_PORT.")
        sys.exit(1)
    print(f"Connecting to {PORT} at {BAUD} baud...")
    ser = serial.Serial(PORT, BAUD, timeout=0.05)
    print("Dispatching STB reboot via SSH...")
    subprocess.Popen(["ssh", "stb", "sudo /sbin/reboot"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print("Listening for U-Boot autoboot countdown...\n")
    start = time.time()
    buf = ""
    in_uboot = False

    while time.time() - start < 45:
        raw = ser.read(ser.in_waiting or 1)
        if raw:
            text = raw.decode("latin-1", errors="ignore")
            sys.stdout.write(text)
            sys.stdout.flush()
            buf += text

            if any(k in buf.lower() for k in ["hit enter", "autoboot", "stop autoboot"]):
                for _ in range(8):
                    ser.write(b" \n")
                    time.sleep(0.05)
                buf = ""
                time.sleep(0.3)

            if any(buf.strip().endswith(p) for p in ["#", "gxl_p212_v1#"]) and not in_uboot:
                print("\n[SUCCESS] Inside vendor U-Boot prompt!")
                in_uboot = True
                time.sleep(0.5)

                chainload_cmds = [
                    "usb start",
                    "fatload usb 0:1 0x1000000 u-boot.ext",
                    "go 0x1000000"
                ]

                for cmd in chainload_cmds:
                    print(f"\n[EXEC U-BOOT]: {cmd}")
                    ser.write(f"{cmd}\n".encode())
                    cmd_start = time.time()
                    cmd_buf = ""
                    limit = 6 if "go" not in cmd else 2
                    while time.time() - cmd_start < limit:
                        r = ser.read(ser.in_waiting or 1)
                        if r:
                            t = r.decode("latin-1", errors="ignore")
                            sys.stdout.write(t)
                            sys.stdout.flush()
                            cmd_buf += t
                            if "#" in cmd_buf and len(cmd_buf) > len(cmd) + 2:
                                break
                        time.sleep(0.02)

                print("\n[MONITORING CHAINLOAD] Observing secondary U-Boot execution for 15s...")
                mon_start = time.time()
                while time.time() - mon_start < 15:
                    r = ser.read(ser.in_waiting or 1)
                    if r:
                        t = r.decode("latin-1", errors="ignore")
                        sys.stdout.write(t)
                        sys.stdout.flush()
                    time.sleep(0.02)
                break
        time.sleep(0.01)

    ser.close()
    print("\nChainload test finished.")

if __name__ == "__main__":
    main()
