# Summary of Work: ZTE ZXV10 B860H Recovery and eMMC Bypass

This document summarizes all the investigations, architectural fixes, repository restructuring, and configuration modifications completed to boot Armbian Linux (Kernel 6.x+) on a ZTE B860H V1/V2 TV Box (Amlogic S905X) with a dead/faulty internal eMMC.

---

## 1. The Core Architecture & Issues Resolved

### A. The Boot Loop & eMMC Writing
- **Problem**: Default Armbian boot scripts (`aml_autoscript`) check and save boot environment states using the U-Boot `saveenv` command. When the onboard eMMC flash is dead or corrupt, writing to its NVRAM fails or hangs, causing U-Boot to reboot in an infinite loop.
- **Fix**: Replaced the default `aml_autoscript` with a custom bypass script. This script directly loads the kernel `Image`, `uInitrd`, and `FDT` from the SD card using `fatload` and boots via `booti` immediately. It skips all NVRAM saving (`saveenv`) and rebooting parameters, terminating the boot loop.

### B. Kernel Relocation (TrustZone Sync Abort)
- **Problem**: Mainline Linux kernels (v5.8+) default to a `text_offset` of `0` in their headers. When the legacy vendor U-Boot calculates the relocation address (`DRAM_BASE + text_offset`), it tries to load the kernel directly to address `0x0`. The first 16MB of DRAM is reserved for the TrustZone Secure Monitor (BL31). Writing here triggers a `Synchronous External Abort` (ESR `0x96000210`) at the hardware level, resetting the board.
- **Fix**: Wrote and applied `patch_image_header.py` to change the `text_offset` field at byte offset 8 of the kernel `Image` file to `0x1080000` (16.5 MB). This relocates the kernel load point safely above the 16MB Secure World boundary.

### C. Wi-Fi GPIO Mismatch (Realtek RTL8189FS)
- **Problem**: The generic reference `p212` Device Tree Blob (DTB) maps the Wi-Fi power reset pin (`sdio-pwrseq`) to GPIO Pin `85`. The ZTE B860H board layout instead connects this reset pin to GPIO Pin `76`. Consequently, the Wi-Fi module remains powered off and invisible to the SDIO bus.
- **Fix**: Refactored `patch_dtb.py` to parse the DTB file structures dynamically. The script scans the device tree structure, finds the `reset-gpios` property of the `sdio-pwrseq` node, and changes the reset pin from `85` (`0x55`) to `76` (`0x4c`) in-place.

---

## 2. Repository Restructuring

The workspace was reorganized from a cluttered root directory into three logical directories to improve maintainability and follow clean coding standards:

```text
d:\STB_B860H/
├── boot/                        # Consolidated bootloader files and scripts
│   ├── legacy/                  # Legacy flashing utilities and param files
│   │   └── usb-unlock/          # Legacy USB unlock files
│   ├── aml_autoscript           # Compiled direct-boot autoscript
│   ├── aml_autoscript.cmd       # Source script code
│   ├── uboot_B860H.bin          # Consolidate B860H U-Boot bin
│   └── uboot_HG680P.bin         # Consolidated HG680P U-Boot bin
├── tools/                       # Flashing, patching and optimization scripts
│   ├── diagnostics/             # Serial monitor, dumper, checking scripts
│   │   ├── find_gpio_offset.py  # Dynamically scans DTB offsets
│   │   └── serial_monitor.py    # Live UART port monitor (default COM9)
│   ├── optimizations/           # Governor and system optimization configs
│   ├── patch_uboot.py           # Injects custom U-Boot into SD sectors
│   ├── patch_dtb.py             # Patches Wi-Fi reset GPIO
│   ├── patch_image_header.py    # Patches kernel load offset
│   └── do_dd.sh                 # Sector injection shell script
├── docs/                        # Complete research and guide files
│   ├── EMMC_BYPASS_RESEARCH.md  # Deep-dive research report on ATF & BootROM
│   ├── RESEARCH_AND_RECOVERY_GUIDE.md  # Step-by-step SD card preparation guide
│   └── SUMMARY_OF_WORK.md       # This work summary
└── live_boot.log                # Live serial monitor logging
```

---

## 3. SD Card (F: Drive) Validation and Modification

When the user mounted the SD card on Windows (allocated as drive `F:\`), we ran diagnostic checks and applied the necessary patches:

1. **Kernel Image (`F:\Image`)**:
   - Detected a default `text_offset` of `0x0`.
   - Executed `patch_image_header.py` and successfully updated the header offset to `0x1080000`.
2. **Device Tree (`F:\dtb\amlogic\meson-gxl-s905x-p212.dtb`)**:
   - Dynamically mapped the DTB nodes and found the Wi-Fi power reset pin property at offset `28256` (`0x6e60`).
   - Executed `patch_dtb.py` and successfully updated the reset pin value from `85` to `76`.
3. **Autoscript (`F:\aml_autoscript`)**:
   - Discovered the SD card had the reboot-prone multi-boot script.
   - Replaced it with the direct-boot `boot/aml_autoscript` version.
4. **Boot Configuration (`F:\uEnv.txt`)**:
   - Read the partition tables of `Armbian_patched.img` using python, located the ext4 Partition 2 superblock, and verified its UUID: `04783cdc-7f19-4f7c-8b96-05afe33d8a46`.
   - Verified that `F:\uEnv.txt` is correctly configured with `root=UUID=04783cdc-7f19-4f7c-8b96-05afe33d8a46`.

---

## 4. Current Status & Verification
All files on the SD card are now fully patched and verified. The next step is to plug the SD card back into the B860H board, connect the UART adapter, and boot the system.

---

## 5. New Hardware Commissioning: Modern Armbian 6.12, PPPwn Purge, eMMC Migration & SD Storage Setup

A new, healthy ZTE ZXV10 B860H hardware unit was acquired to replace the previous unit with dead hardware eMMC. This new unit was originally flashed by a marketplace seller with `STB-Pwn` (a PS4 PPPwn jailbreak dongle firmware). We executed an end-to-end overhaul:

### A. Security Audit & PPPwn Purge
- **Initial Access**: Gained root shell via unauthenticated Nginx/PHP-FPM web UI left by the seller on port 80 running with `www-data ALL=(ALL) NOPASSWD: ALL` in sudoers.
- **Purged Artifacts**: Removed `pipwn`, `pppoe`, `dtlink` daemons, killed running `pppwn64` process, purged Nginx and PHP packages, and cleaned `/etc/rc.local`.
- **Cleaned `/boot` Partition**: Deleted over 50 MB of leftover seller APK files and corrupted `FSCK*.REC` records that filled the 122MB FAT boot partition.
- **Credential Setup**: Set password for `root` and created administrative user `trefeon` (`<stb-password>`).

### B. Modern Armbian 6.12 LTS Deployment
- **Image Selected**: `Armbian_26.11.0_amlogic_s905x-b860h_bookworm_6.12.112_server_2026.10.15` (Debian 12 Bookworm, Kernel 6.12.112 LTS by Ophub).
- **Turnkey Windows Flashing**: Wrote `tools/download_and_prep_image.py` (downloaded and decompressed 3.5GB raw image) and `tools/flash_sd.py` (direct block writing via Win32 ctypes API to `\\.\PhysicalDrive2` at 16.2 MB/s).
- **Initramfs Timeout Fix**: Resolved `ALERT! UUID=... does not exist` by configuring `root=LABEL=ROOTFS rootdelay=10` in `uEnv.txt`.

### C. Full eMMC Migration (`armbian-install`)
- Executed `armbian-install` with Box ID `106` (`B860H`, `meson-gxl-s905x-b860h.dtb`).
- Partitioned internal eMMC (`/dev/mmcblk2`) with a modern 512MB boot partition (`BOOT_EMMC`) and 6.1GB root filesystem (`ROOTFS_EMMC`).

### D. Virtual Swap Memory & SD Storage Repurposing
- **Virtual Memory**: Created 2GB persistent `/swapfile` on eMMC root, configured `/etc/fstab`, and applied sysctl tuning (`vm.swappiness=60`, `vm.vfs_cache_pressure=50`).
- **MicroSD Repurposing**: Formatted the 32GB MicroSD card (`/dev/mmcblk1`) to a single ext4 partition (`SD_STORAGE`) via `/root/setup_sd_storage.sh`.
- **Auto-mount & Symlinks**: Bound `LABEL=SD_STORAGE` to `/mnt/storage` with `nofail` in `/etc/fstab`, and created direct user symlink `/home/<user>/storage`.
- **Active Endpoint**: Verified STB running cleanly at `<STB-LAN-IP>` with zero failed systemd services and CPU temperature at 36°C.

---

## 6. Docker CE, Total SD Offloading, Tailscale Mesh & Native SSH Tooling

### A. Total eMMC Offloading (Bind-Mounts)
- Offloaded `/home/<user>` and `/opt` entirely to the 30GB MicroSD card (`/mnt/storage`) via `/etc/fstab` bind-mounts.
- Configured systemd journald log capping (`MaxUse=50M`) and automatic APT package cache purging (`APT::Keep-Downloaded-Packages "false"`).
- The internal 8GB eMMC (`/dev/mmcblk2p2`, 6.1GB rootfs) maintains **3.7 GB free space (39% used)** permanently.

### B. Docker CE & Docker Compose
- Installed official Docker CE 29.9.2 and Docker Compose plugin 5.6.1 on ARM64.
- Configured Docker daemon root to MicroSD (`"data-root": "/mnt/storage/docker"` in `/etc/docker/daemon.json`), ensuring all images, layers, and volumes live on the SD card.
- Added `trefeon` to the `docker` group for passwordless container execution.

### C. Wi-Fi Failover & Network Routing
- Fixed driver out-of-tree Realtek RTL8189FS for Linux Kernel 6.12 via `tools/auto_patch_wifi_bt.sh` and disabled phantom Broadcom Bluetooth in the DTB.
- Configured automatic failover routing: Ethernet `eth0` at `metric 100` (Primary 100 Mbps, 9.17 MB/s real throughput) and Wi-Fi `wlan0` at `metric 600` (Seamless backup, `powersave: off`).

### D. Tailscale Mesh & Passwordless Native SSH
- Installed Tailscale v1.104.2 on the STB (`<TAILSCALE-IP>`) connected to `<your-tailnet>.ts.net`.
- Registered Windows ED25519 public key into STB `authorized_keys`.
- Added shortcuts in `~/.ssh/config` (`ssh stb`, `ssh stb-wifi`, `ssh stb-ts`).
- Migrated all diagnostic and optimization tooling from Python/Paramiko to native Bash scripts (`tools/diagnostics/*.sh`, `tools/optimizations/*.sh`), eliminating external Python dependencies.

---

## 7. Cold Boot Blackscreen Resolution, U-Boot NVRAM Persistence & Offline Packages

### A. The MicroSD x86 MBR Crash Trap
- **Issue**: When formatting the MicroSD card with `parted mklabel msdos`, standard x86 bootstrap machine code was written to sector 0 (bytes 0–445). Because Amlogic hardware BootROM prioritizes the MicroSD slot over eMMC, the ARM64 Cortex-A53 processor attempted to execute x86 instructions, triggering an illegal instruction crash before eMMC was probed.
- **Fix**: Developed `tools/sanitize_sd_mbr.py` to zero out bytes 0–445 while preserving the partition table (bytes 446–509) and the `0x55AA` signature, allowing clean BootROM fallback to eMMC.

### B. eMMC U-Boot NVRAM `bootcmd` Resolution
- **Issue**: The `armbian-install` script populated the FAT32 boot partition (`mmc 1:1`), but left the vendor U-Boot NVRAM environment (`0x3ee00000`) untouched (`bootcmd=run storeboot`). On cold boot, U-Boot fell back to an interactive prompt `gxl_p212_v1#` because Android kernel was missing, causing a persistent black screen on HDMI.
- **Fix**: Captured the live U-Boot shell via hardware UART `X2` (COM5 @ 115200 baud) and permanently committed the autoboot sequence to eMMC NVRAM via `saveenv`:
  ```bash
  setenv bootcmd "if fatload mmc 1:1 0x1020000 emmc_autoscript; then autoscr 0x1020000; fi; if fatload mmc 0:1 0x1020000 s905_autoscript; then autoscr 0x1020000; fi; run storeboot"
  saveenv
  ```

### C. Pre-Built Offline Patch Package (`packages/b860h_patch/`)
- Extracted tested production binaries directly from the live STB:
  - `packages/b860h_patch/8189fs.ko` (3.05 MB)
  - `packages/b860h_patch/meson-gxl-s905x-b860h.dtb` (40.8 KB)
- Created turnkey installer `packages/b860h_patch/install.sh` and host deployment script `tools/ship_patch.sh` for instant, offline Wi-Fi & Bluetooth patching on newly installed units without downloading or compiling.
