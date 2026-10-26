#!/usr/bin/env python3
"""
Interactive U-Boot probe and test via <COM-PORT> (e.g. COM5 on Windows).
Catches U-Boot prompt on reboot, runs diagnostics, and tests USB booting.
"""

import sys
import os
import time
import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("STB_COM_PORT", "<COM-PORT>")
BAUD = 115200
LOG_FILE = "live_uboot_test.log"

def main():
    if PORT == "<COM-PORT>":
        print("ERROR: no serial port given. Pass it as argv[1] (e.g. COM5 on Windows) or set STB_COM_PORT.")
        sys.exit(1)
    print(f"Opening {PORT} at {BAUD} baud...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.1)
    except Exception as e:
        print(f"Error opening {PORT}: {e}")
        sys.exit(1)

    print(f"Connected to {PORT}!")
    print(f"Listening for U-Boot countdown and logging to {LOG_FILE}...\n")

    in_uboot = False
    buf = ""

    with open(LOG_FILE, "w", encoding="utf-8", errors="ignore") as log:
        log.write(f"=== U-BOOT PROBE STARTED AT {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        log.flush()

        start_time = time.time()
        while time.time() - start_time < 45:
            raw = ser.read(ser.in_waiting or 1)
            if raw:
                text = raw.decode("latin-1", errors="ignore")
                sys.stdout.write(text)
                sys.stdout.flush()
                log.write(text)
                log.flush()
                buf += text

                # Interrupt autoboot
                if any(k in buf.lower() for k in ["hit enter", "autoboot", "stop autoboot"]):
                    print("\n[ACTION] Detected autoboot countdown! Sending interrupts...")
                    for _ in range(5):
                        ser.write(b"   \n")
                        time.sleep(0.05)
                    buf = ""
                    time.sleep(0.5)

                # Detect U-Boot prompt (#)
                if any(buf.strip().endswith(p) for p in ["#", "B860H#", "p212#", "gxl#"]) and not in_uboot:
                    print("\n[SUCCESS] Entered U-Boot interactive shell!")
                    in_uboot = True
                    time.sleep(0.5)

                    commands = [
                        "version",
                        "usb start",
                        "usb info",
                        "fatls usb 0:1",
                        "printenv bootargs",
                        "printenv bootcmd",
                    ]

                    for cmd in commands:
                        print(f"\n[RUNNING U-BOOT CMD]: {cmd}")
                        ser.write(f"{cmd}\n".encode())
                        cmd_start = time.time()
                        cmd_buf = ""
                        while time.time() - cmd_start < 4:
                            r = ser.read(ser.in_waiting or 1)
                            if r:
                                t = r.decode("latin-1", errors="ignore")
                                sys.stdout.write(t)
                                sys.stdout.flush()
                                log.write(t)
                                log.flush()
                                cmd_buf += t
                                if "#" in cmd_buf and len(cmd_buf) > len(cmd) + 2:
                                    break
                            time.sleep(0.02)

                    print("\n[DIAGNOSTICS COMPLETE] Resuming normal boot into Linux Armbian...")
                    ser.write(b"run bootcmd\n")
                    time.sleep(3.0)
                    break

            time.sleep(0.01)

    ser.close()
    print("\nProbe finished.")

if __name__ == "__main__":
    main()
