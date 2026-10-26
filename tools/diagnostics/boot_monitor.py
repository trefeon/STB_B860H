#!/usr/bin/env python3
"""Smart STB boot monitor on <COM-PORT> (e.g. COM5 on Windows).

Event-driven (no blind timeouts): every boot session ends the moment its
outcome is known, and the verdict names WHICH boot finished or got stuck.

End states (closed immediately, after a short settle delay):
  OK login            -> `armbian login:` seen (Linux fully booted)
  STOPPED at prompt   -> `gxl_p212_v1#` seen after autoboot already ran
  STUCK initramfs     -> `(initramfs)` prompt seen
  STUCK no kernel     -> `Starting kernel` with no Linux logs afterwards
  STUCK silent        -> fallback: no output at all for --stuck seconds

Usage:
    python tools/diagnostics/boot_monitor.py [--port <COM-PORT>]
        [--settle 3.0] [--stuck 25] [--kernel-wait 60] [--dir logs]
"""
import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import serial

BAUD = 115200

RE_BOOT_START = re.compile(r"U-Boot 2015\.01|set vcck to")
RE_AUTOBOOT = re.compile(r"Hit Enter or space")
RE_UBOOT_PROMPT = re.compile(r"gxl_p212_v1#")
RE_KERNEL_START = re.compile(r"Starting kernel")
RE_LINUX_BOOT = re.compile(r"Booting Linux on physical CPU")
RE_LOGIN = re.compile(r"armbian login:")
RE_INITRAMFS = re.compile(r"\(initramfs\)")
RE_LINUX_VER = re.compile(r"Linux version (\S+)")
RE_PANIC = re.compile(r"Kernel panic|Oops:|InitFatalReboot")


class BootSession:
    def __init__(self, logdir: Path, settle: float):
        self.logdir = logdir
        self.settle = settle
        self.lines: list[str] = []
        self.t0: float | None = None
        self.t_kernel: float | None = None
        self.t_linux: float | None = None
        self.t_login: float | None = None
        self.saw_autoboot = False
        self.saw_prompt = False
        self.saw_initramfs = False
        self.linux_ver = ""
        self.fh = None
        self.fname = ""
        self.last_rx = time.time()
        self.done = False
        self.done_at = 0.0

    def _stamp(self, now: float) -> str:
        rel = now - self.t0 if self.t0 else 0.0
        wall = datetime.now().strftime("%H:%M:%S")
        return f"[+{rel:7.2f}s {wall}] "

    def open(self, now: float):
        self.t0 = now
        self.last_rx = now
        self.fname = datetime.now().strftime("boot_%Y%m%d_%H%M%S.log")
        self.fh = open(self.logdir / self.fname, "w", encoding="utf-8", errors="ignore")
        self.fh.write(f"### boot started {datetime.now().isoformat()} ###\n")

    def feed(self, text: str, now: float):
        if self.t0 is None:
            self.open(now)
        self.last_rx = now
        for line in text.splitlines(keepends=True):
            s = line.strip()
            self.fh.write(self._stamp(now) + line if line.endswith("\n") else self._stamp(now) + line + "\n")
            self.fh.flush()
            if RE_AUTOBOOT.search(s):
                self.saw_autoboot = True
            if RE_UBOOT_PROMPT.search(s):
                self.saw_prompt = True
                self._maybe_done(now)
            if RE_KERNEL_START.search(s) and self.t_kernel is None:
                self.t_kernel = now
            if RE_LINUX_BOOT.search(s) and self.t_linux is None:
                self.t_linux = now
            m = RE_LINUX_VER.search(s)
            if m:
                self.linux_ver = m.group(1)
            if RE_LOGIN.search(s) and self.t_login is None:
                self.t_login = now
                self._maybe_done(now)
            if RE_INITRAMFS.search(s):
                self.saw_initramfs = True
                self._maybe_done(now)
            if RE_PANIC.search(s):
                self._maybe_done(now, forced=f"STUCK kernel panic/fatal: {s[:100]}")

    def _maybe_done(self, now: float, forced: str | None = None):
        if self.done:
            return
        self.done = True
        self.done_at = now
        self.forced = forced

    def ready_to_close(self, now: float, stuck: float, kernel_wait: float) -> str | None:
        """Return a close reason when the outcome is certain, else None."""
        if self.t0 is None:
            return None
        if self.done and now - self.done_at >= self.settle:
            return "settled"
        # Starting kernel but no Linux logs within kernel_wait -> stuck, no need to wait for silence.
        if self.t_kernel is not None and self.t_linux is None and now - self.t_kernel >= kernel_wait:
            return f"no Linux logs {kernel_wait:.0f}s after 'Starting kernel'"
        # Fallback: total silence.
        if now - self.last_rx >= stuck:
            return f"silent {stuck:.0f}s"
        return None

    def _dur(self, t: float | None) -> str:
        return f"{t - self.t0:.1f}s" if t and self.t0 else "-"

    def verdict(self) -> str:
        if getattr(self, "forced", None):
            return self.forced
        if self.t_login is not None:
            return (f"OK login t+{self._dur(self.t_login)} "
                    f"(kernel t+{self._dur(self.t_kernel)}, {self.linux_ver})")
        if self.saw_initramfs:
            return f"STUCK initramfs t+{self._dur(self.t_kernel)}, root not mounted"
        if self.t_linux is not None:
            return f"STUCK booting t+{self._dur(self.t_linux)}, no login yet"
        if self.t_kernel is not None:
            return "STUCK after 'Starting kernel', no Linux logs"
        if self.saw_prompt:
            return "STOPPED at U-Boot prompt (autoboot script did not run)"
        if self.saw_autoboot:
            return "STUCK in autoboot countdown"
        return "STUCK early U-Boot (no autoboot line seen)"

    def close(self, reason: str):
        if self.t0 is None or self.fh is None:
            return None
        v = self.verdict()
        self.fh.write(f"### {reason}: {v} ###\n")
        self.fh.close()
        line = f"{self.fname} :: {v}"
        with open(self.logdir / "boots_summary.log", "a", encoding="utf-8") as sf:
            sf.write(f"{datetime.now().isoformat()} {line}\n")
        self.t0 = None
        self.fh = None
        self.done = False
        return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=os.environ.get("STB_COM_PORT"),
                    help="Serial port (<COM-PORT>; e.g. COM5 on Windows) or STB_COM_PORT env")
    ap.add_argument("--settle", type=float, default=3.0)
    ap.add_argument("--stuck", type=float, default=25.0)
    ap.add_argument("--kernel-wait", type=float, default=60.0)
    ap.add_argument("--dir", default="logs")
    args = ap.parse_args()

    if not args.port:
        ap.error("no serial port: pass --port <COM-PORT> (e.g. COM5 on Windows) or set STB_COM_PORT")

    logdir = Path(args.dir)
    logdir.mkdir(parents=True, exist_ok=True)
    ser = serial.Serial(args.port, BAUD, timeout=0.2)
    print(f"Listening on {args.port} (settle {args.settle}s, "
          f"silent-fallback {args.stuck}s, kernel-wait {args.kernel_wait}s). Ctrl+C to stop.")
    sess = BootSession(logdir, args.settle)
    try:
        while True:
            raw = ser.read(ser.in_waiting or 1)
            now = time.time()
            if raw:
                text = raw.decode("latin-1", errors="ignore")
                if RE_BOOT_START.search(text) and sess.t0 is not None:
                    done = sess.close("new boot detected")
                    if done:
                        print(f"<<< {done}")
                    sess = BootSession(logdir, args.settle)
                sess.feed(text, now)
                sys.stdout.write(text)
                sys.stdout.flush()
            reason = sess.ready_to_close(now, args.stuck, args.kernel_wait)
            if reason is not None:
                done = sess.close(reason)
                if done:
                    print(f"\n<<< {done}")
                sess = BootSession(logdir, args.settle)
            else:
                time.sleep(0.05)
    except KeyboardInterrupt:
        done = sess.close("monitor stopped")
        if done:
            print(f"<<< {done}")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
