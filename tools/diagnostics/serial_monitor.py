#!/usr/bin/env python3
"""
Serial monitor for B860H UART boot output.
Auto-detects CH340 USB-to-serial adapter. Falls back to manual port selection.

Usage:
  python serial_monitor.py              # auto-detect CH340
  python serial_monitor.py --port COM9  # force a specific port
  python serial_monitor.py --baud 9600  # custom baud rate
"""
import sys
import time
import argparse
import serial
import serial.tools.list_ports
from serial.serialutil import SerialException

BAUDRATE_DEFAULT = 115200
LOG_FILE = 'live_boot.log'

# CH340 USB VID:PID identifiers
CH340_IDENTIFIERS = [
    {"vid": 0x1A86, "pid": 0x7523},   # CH340
    {"vid": 0x1A86, "pid": 0x7522},   # CH340B
    {"vid": 0x1A86, "pid": 0x5523},   # CH341 in serial mode
    {"vid": 0x1A86, "pid": 0x55D4},   # CH9102 (CH341 family)
    {"vid": 0x1A86, "pid": 0xEC31},   # CH343
]
CH340_DESC_KEYWORDS = ["ch340", "ch341", "ch9102", "usb serial", "usb-serial"]


def detect_ch340():
    """Scan connected COM ports and return the first CH340 found."""
    ports = serial.tools.list_ports.comports()
    ch340_ports = []

    for p in ports:
        matched = False
        # Match by VID:PID
        if p.vid is not None and p.pid is not None:
            for ident in CH340_IDENTIFIERS:
                if p.vid == ident["vid"] and p.pid == ident["pid"]:
                    matched = True
                    break
        # Match by description string (fallback)
        if not matched and p.description:
            desc_lower = p.description.lower()
            if any(kw in desc_lower for kw in CH340_DESC_KEYWORDS):
                matched = True

        if matched:
            ch340_ports.append(p)

    return ch340_ports


def pick_port(forced_port=None):
    """Resolve the serial port to use."""
    if forced_port:
        print(f"[Port] Using forced port: {forced_port}")
        return forced_port

    print("[Scan] Scanning for CH340 USB serial adapters...")
    found = detect_ch340()

    if len(found) == 1:
        p = found[0]
        print(f"[Found] {p.device} — {p.description} (VID:{p.vid:04X} PID:{p.pid:04X})")
        return p.device

    elif len(found) > 1:
        print("[Found] Multiple CH340 adapters detected:")
        for i, p in enumerate(found):
            vid = f"{p.vid:04X}" if p.vid else "????"
            pid = f"{p.pid:04X}" if p.pid else "????"
            print(f"  [{i}] {p.device} — {p.description} (VID:{vid} PID:{pid})")
        idx = input("Select adapter index [0]: ").strip() or "0"
        return found[int(idx)].device

    else:
        # No CH340 found — list all ports and let user pick
        all_ports = serial.tools.list_ports.comports()
        if all_ports:
            print("[Warn] No CH340 found. All available ports:")
            for i, p in enumerate(all_ports):
                print(f"  [{i}] {p.device} — {p.description}")
            idx = input("Select port index (or Enter to type manually): ").strip()
            if idx.isdigit():
                return all_ports[int(idx)].device
        port = input("Enter COM port manually (e.g. COM9): ").strip()
        return port


def monitor_serial(port, baudrate):
    ser = None
    print("\n=== B860H UART Serial Monitor ===")
    print(f"    Port    : {port}")
    print(f"    Baud    : {baudrate}")
    print(f"    Log file: {LOG_FILE}")
    print("    Press Ctrl+C to stop.\n")

    log_f = open(LOG_FILE, 'a', encoding='utf-8', errors='replace')

    while True:
        try:
            if ser is None or not ser.is_open:
                msg = f"[Connecting] Opening {port}..."
                print(msg, end="", flush=True)
                log_f.write(msg)
                log_f.flush()

                ser = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=0.1,
                )
                print(" Connected!")
                log_f.write(" Connected!\n")
                log_f.flush()

            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                text = data.decode('utf-8', errors='replace')
                sys.stdout.write(text)
                sys.stdout.flush()
                log_f.write(text)
                log_f.flush()

            time.sleep(0.01)

        except SerialException as se:
            if "PermissionError" in str(se) or "Access is denied" in str(se):
                err_msg = f"\n[Error] Port {port} is busy or access denied. Retrying in 2s...\n"
            else:
                err_msg = f"\n[Disconnected] {se}. Reconnecting in 2s...\n"

            print(err_msg, end="", flush=True)
            log_f.write(err_msg)
            log_f.flush()

            if ser:
                try:
                    ser.close()
                except Exception:
                    pass
                ser = None
            time.sleep(2)

        except KeyboardInterrupt:
            stop_msg = "\n=== Monitoring stopped by user ===\n"
            print(stop_msg, end="")
            log_f.write(stop_msg)
            log_f.flush()
            if ser:
                ser.close()
            log_f.close()
            break


def main():
    parser = argparse.ArgumentParser(description="B860H UART serial monitor with CH340 auto-detection")
    parser.add_argument("--port", help="Force a specific COM port (e.g. COM9)")
    parser.add_argument("--baud", type=int, default=BAUDRATE_DEFAULT, help=f"Baud rate (default: {BAUDRATE_DEFAULT})")
    args = parser.parse_args()

    port = pick_port(args.port)
    if not port:
        print("[Error] No port selected. Exiting.")
        sys.exit(1)

    monitor_serial(port, args.baud)


if __name__ == "__main__":
    main()
