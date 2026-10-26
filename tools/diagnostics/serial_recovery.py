#!/usr/bin/env python3
"""
Automated Serial Recovery for B860H via serial port (STB_COM_PORT env,
or pass port as argv[1]).
Reads boot logs in real time, auto-responds to login/shell prompts,
and restores /boot/emmc_autoscript from backup.

No credential is stored in this file: the login password is read from the
STB_PASSWORD environment variable, or from an interactive prompt.
Usage:
  STB_PASSWORD='<stb-password>' python tools/diagnostics/serial_recovery.py [<COM-PORT>]
  (e.g. COM5 on Windows)
"""

import sys
import os
import getpass
import time
import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("STB_COM_PORT", "<COM-PORT>")
BAUD = 115200
LOG_FILE = "live_recovery.log"

def main():
    if PORT == "<COM-PORT>":
        print("ERROR: no serial port given. Pass it as argv[1] (e.g. COM5 on Windows) or set STB_COM_PORT.")
        sys.exit(1)
    password = os.environ.get("STB_PASSWORD") or getpass.getpass("STB login password (<stb-password>): ")
    print(f"Connecting to {PORT} at {BAUD} baud...")
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.1)
    except Exception as e:
        print(f"Failed to open {PORT}: {e}")
        sys.exit(1)

    print(f"Connected to {PORT}! Listening for STB power cycle / boot output...")
    print(f"Logging output to {LOG_FILE}\n")

    buf = ""
    logged_in = False
    restored = False
    start_time = time.time()

    with open(LOG_FILE, "a", encoding="utf-8", errors="ignore") as log:
        log.write(f"\n--- SERIAL RECOVERY SESSION STARTED AT {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        log.flush()

        while True:
            # Read all available bytes
            raw = ser.read(ser.in_waiting or 1)
            if raw:
                text = raw.decode("latin-1", errors="ignore")
                sys.stdout.write(text)
                sys.stdout.flush()
                log.write(text)
                log.flush()
                buf += text

                # Keep last 2048 chars in buffer
                if len(buf) > 4096:
                    buf = buf[-2048:]

                # 1. Detect Linux Login Prompt
                if ("login:" in buf.lower() or "armbian login:" in buf.lower()) and not logged_in:
                    print("\n[ACTION] Detected Login Prompt! Sending username 'root'...")
                    time.sleep(0.5)
                    ser.write(b"root\n")
                    buf = ""
                    time.sleep(1.0)

                # 2. Detect Password Prompt
                if "password:" in buf.lower() and not logged_in:
                    print("\n[ACTION] Detected Password Prompt! Sending configured password...")
                    time.sleep(0.5)
                    ser.write(password.encode() + b"\n")
                    buf = ""
                    logged_in = True
                    time.sleep(1.5)

                # 3. Detect Root Shell Prompt (# or root@)
                if ("root@" in buf or "#" in buf) and not restored:
                    print("\n[ACTION] Root shell active! Restoring original emmc_autoscript...")
                    ser.write(b"cp -f /boot/emmc_autoscript.bak /boot/emmc_autoscript && sync && echo RESTORE_SUCCESS\n")
                    time.sleep(1.0)
                    restored = True
                    buf = ""

                # 4. Check for success confirmation
                if "RESTORE_SUCCESS" in buf:
                    print("\n[SUCCESS] /boot/emmc_autoscript restored to original backup!")
                    print("[ACTION] Rebooting STB into clean Linux Armbian...")
                    ser.write(b"reboot\n")
                    time.sleep(2.0)
                    break

                # 5. Detect initramfs emergency shell
                if "(initramfs)" in buf and not restored:
                    print("\n[ACTION] Detected initramfs prompt! Mounting eMMC and restoring...")
                    ser.write(b"mkdir -p /boot && mount /dev/mmcblk2p1 /boot && cp -f /boot/emmc_autoscript.bak /boot/emmc_autoscript && sync && reboot -f\n")
                    time.sleep(2.0)
                    restored = True
                    buf = ""

            time.sleep(0.01)

    ser.close()
    print("Recovery session finished.")

if __name__ == "__main__":
    main()
