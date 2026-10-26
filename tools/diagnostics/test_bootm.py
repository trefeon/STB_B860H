#!/usr/bin/env python3
"""Boot an image via U-Boot `bootm` on <COM-PORT> (e.g. COM5 on Windows).
(consolidates test_boot_stock.py, test_bootm.py, boot_android_test.py).

Usage:
    python tools/diagnostics/test_bootm.py [--port <COM-PORT>] [--image boot.img]
        [--addr 0x12000000] [--bootargs "root=/dev/sda2 rootwait ..."]
        [--monitor 15]

Flow: `ssh stb reboot` -> catch autoboot countdown -> `usb start` ->
`fatload usb 0:1 <addr> <image>` -> optional `setenv bootargs` ->
`bootm <addr>` -> watch kernel output for <monitor> seconds.
"""

import argparse
import os
import subprocess
import sys
import time

import serial


def run_uboot_cmd(ser, cmd, wait=8.0):
    print(f"\n[EXEC U-BOOT]: {cmd}")
    ser.write(f"{cmd}\n".encode())
    t0 = time.time()
    while time.time() - t0 < wait:
        r = ser.read(ser.in_waiting or 1)
        if r:
            sys.stdout.write(r.decode("latin-1", errors="ignore"))
            sys.stdout.flush()
        time.sleep(0.02)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=os.environ.get("STB_COM_PORT"),
                    help="Serial port (<COM-PORT>; e.g. COM5 on Windows) or STB_COM_PORT env")
    ap.add_argument("--image", default="boot.img")
    ap.add_argument("--addr", default="0x12000000")
    ap.add_argument("--bootargs", default="")
    ap.add_argument("--monitor", type=int, default=15)
    args = ap.parse_args()

    print(f"Opening {args.port} at 115200 baud...")
    ser = serial.Serial(args.port, 115200, timeout=0.05)

    print("Triggering STB reboot via SSH...")
    subprocess.Popen(["ssh", "stb", "sudo /sbin/reboot"],
                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print("Catching U-Boot prompt...\n")
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

            if buf.strip().endswith(("gxl_p212_v1#", "#")) and not in_uboot:
                print("\n[SUCCESS] Inside U-Boot prompt!")
                in_uboot = True
                time.sleep(0.5)

                run_uboot_cmd(ser, "usb start")
                run_uboot_cmd(ser, f"fatload usb 0:1 {args.addr} {args.image}")
                if args.bootargs:
                    run_uboot_cmd(ser, f'setenv bootargs "{args.bootargs}"', wait=2.0)
                run_uboot_cmd(ser, f"bootm {args.addr}", wait=2.0)

                print(f"\n[MONITORING] Observing kernel reaction for {args.monitor}s...")
                mon_start = time.time()
                while time.time() - mon_start < args.monitor:
                    r = ser.read(ser.in_waiting or 1)
                    if r:
                        sys.stdout.write(r.decode("latin-1", errors="ignore"))
                        sys.stdout.flush()
                    time.sleep(0.02)
                break
        time.sleep(0.01)

    ser.close()
    print("\nBootm test finished.")


if __name__ == "__main__":
    main()
