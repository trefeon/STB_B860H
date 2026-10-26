# Self-Healing Boot — B860H Low-Level Review

Goal: every future update/failure boots without UART. UART stays as last resort, never as procedure.

## Boot chain and SPOF map

| Stage | Owner | Fails how | Self-heal | Residual |
|---|---|---|---|---|
| BootROM → SPL → U-Boot | eMMC sectors 0–4MB (HG680P-derived, verified 26B MBR diff) | eMMC death, bad flash | SD-bypass via raw-sector inject (`patch_uboot.py`) | Needs physical SD + power cycle. eFuse keynum=4: only signed chain boots, never reflash blind. |
| NVRAM env (`0x3ee00000`, AES-opaque) | `bootcmd` one-liner | env loss → `run storeboot` dead end (proven: storeboot probes no files, `storeboot_probe.log`) | None possible in-vendor-env (default path loads nothing). Prevention: zero future `saveenv`; fallback logic lives in files, not env. | Single NVRAM line remains. UART recovery documented (`uart_shell.py`). |
| Autoscript | /boot, mkimage on-STB | bad edit, CRLF | Fallback block, no env, no conditionals. PROVEN 2026-10-26: primary removed, .good booted, login t+34.5s. | Half-written primary plus booti on garbage can hang; snapshot SOP covers it. |
| Kernel/initrd/DTB | deb + updater | new-kernel panic, DTB regress, `.ko` vermagic | A/B slots: `.good` set promoted pre-update; fallback block boots it. Userspace detects foreign kernel via `uname -r` vs `/boot/.expected_kernel`. | First boot of a new kernel is still the test. Never delete `.good` until new set verified. |
| Userspace/services/net | systemd, NM, Tailscale, Docker | hang on shutdown/reboot, service fail | `RuntimeWatchdogSec=30` + `ShutdownWatchdogSec=5min` (`meson_gxbb_wdt`, built-in) forces HW reset. Hotspot failover covers uplink loss. | Watchdog needs userspace alive enough to pet (kernel petting). U-Boot prompt hangs are out of scope (no WDT there). |
| Rootfs/SD storage | ext4, fstab `nofail` | SD death, corrupt fs | `nofail` everywhere boots without SD; bind mounts degrade, system survives. `fsck.fix=yes` on cmdline. | Data on dead SD still needs physical swap. |

## Update SOP (mandatory order)

1. `tools/snapshot_boot_good.sh` — promote running set to `.good`, write `/boot/.expected_kernel`.
2. `armbian-update -k <ver> -u stable` (with `-b no` on reinstall).
 3. Re-patch DTB + rebuild `8189fs` (ship_patch flow); refresh `packages/b860h_patch/`.
4. Reboot, verify `uname -r` == expected + `wlan0` + no failed services.
5. Only then the new set is good; re-run snapshot to promote it.

## What "no UART" means concretely

- Kernel panic on new version → U-Boot fallback boots `.good` → SSH/Tailscale up on old kernel → fix remotely.
- Shutdown/reboot hang → hardware watchdog resets the SoC.
- Service/net failure → failover + watchdog + remote SSH.
- Env loss / bootloader damage → UART (accepted residual; probability minimized, recovery tooled).
