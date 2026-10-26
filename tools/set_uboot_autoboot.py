#!/usr/bin/env python3
"""
Automatically connects to ZTE B860H U-Boot prompt over USB serial (CH340/COM)
and commits the permanent autoboot command to eMMC NVRAM via saveenv.

Usage:
  python tools/set_uboot_autoboot.py [--port <COM-PORT>] [--baud 115200]
  (e.g. --port COM5 on Windows; auto-detects CH340/CP210/FTDI adapters when omitted)
"""

import sys
import time
import argparse
import serial
import serial.tools.list_ports

UBOOT_PROMPT = b"gxl_p212_v1#"
BOOTCMD_PAYLOAD = (
    'setenv bootcmd "if fatload mmc 1:1 0x1020000 emmc_autoscript; then autoscr 0x1020000; fi; '
    'if fatload mmc 0:1 0x1020000 s905_autoscript; then autoscr 0x1020000; fi; run storeboot"\n'
)

def auto_detect_port():
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").lower()
        if any(k in desc for k in ["ch340", "ch341", "usb serial", "usb-serial", "cp210", "ftdi"]):
            return p.device
    if ports:
        return ports[0].device
    return None

def main():
    parser = argparse.ArgumentParser(description="Set permanent U-Boot autoboot command in B860H eMMC NVRAM")
    parser.add_argument("--port", help="Serial port (<COM-PORT>; e.g. COM5 on Windows)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    args = parser.parse_args()

    port = args.port or auto_detect_port()
    if not port:
        print("ERROR: No serial port found. Please connect your USB TTL adapter.")
        sys.exit(1)

    print(f"[Connecting] Opening {port} at {args.baud} baud...")
    ser = serial.Serial(port, args.baud, timeout=0.1)
    
    print("[Waiting] Listening for U-Boot prompt 'gxl_p212_v1#'...")
    print("If STB is off, power it on now. Sending wake triggers...")
    
    start = time.time()
    caught = False
    while time.time() - start < 20:
        ser.write(b" \n")
        ser.flush()
        time.sleep(0.05)
        n = ser.in_waiting
        if n > 0:
            chunk = ser.read(n)
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
            if UBOOT_PROMPT in chunk:
                caught = True
                break

    if not caught:
        print("\n[Error] U-Boot prompt was not caught within 20s.")
        ser.close()
        sys.exit(1)

    print("\n[Action] Configuring permanent autoboot environment...")
    time.sleep(0.3)
    ser.reset_input_buffer()

    ser.write(BOOTCMD_PAYLOAD.encode("utf-8"))
    ser.flush()
    time.sleep(0.5)
    print(ser.read(ser.in_waiting).decode("utf-8", errors="replace"))

    print("[Action] Committing to eMMC NVRAM via saveenv...")
    ser.write(b"saveenv\n")
    ser.flush()
    time.sleep(1.2)
    saveenv_out = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
    print(saveenv_out)

    if "done" in saveenv_out.lower() or "writing to mmc" in saveenv_out.lower():
        print("[SUCCESS] Permanent autoboot written to eMMC NVRAM!")
        print("[Action] Booting Armbian now...")
        ser.write(b"run bootcmd\n")
        ser.flush()
    else:
        print("[Warn] saveenv did not confirm 'done'. Please inspect output above.")

    ser.close()

if __name__ == "__main__":
    main()
