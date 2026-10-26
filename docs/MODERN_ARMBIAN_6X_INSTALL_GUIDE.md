# Complete Guide: Modern Armbian Installation (Kernel 6.x LTS), PPPwn Cleanup, eMMC Migration, and MicroSD Storage on the ZTE B860H

This guide documents the technical investigation, cleanup of third-party firmware (PPPwn PS4 HEN), installation of **modern Armbian (Debian 12 Bookworm / Linux Kernel 6.12.y LTS)**, migration of the system to the internal eMMC, Swap Memory setup, and use of a MicroSD card as permanent internal storage media on the **ZTE ZXV10 B860H V1/V2 (Amlogic S905X)** STB.

---

## 📋 Table of Contents
1. [Identifying & Cleaning Marketplace Firmware Leftovers (PPPwn)](#1-identifying--cleaning-marketplace-firmware-leftovers-pppwn)
2. [Image Selection & Modern MicroSD Preparation (Kernel 6.12 LTS)](#2-image-selection--modern-microsd-preparation-kernel-612-lts)
3. [MicroSD Boot Troubleshooting: Fixing the Initramfs ALERT UUID](#3-microsd-boot-troubleshooting-fixing-the-initramfs-alert-uuid)
4. [Migrating the System to Internal eMMC (`armbian-install`)](#4-migrating-the-system-to-internal-emmc-armbian-install)
5. [Virtual Swap Memory Configuration (Companion to 2GB RAM)](#5-virtual-swap-memory-configuration-companion-to-2gb-ram)
6. [Configuring MicroSD as Permanent Internal Storage](#6-configuring-microsd-as-permanent-internal-storage)
7. [Repository Automation & Diagnostic Scripts](#7-repository-automation--diagnostic-scripts)

---

## 1. Identifying & Cleaning Marketplace Firmware Leftovers (PPPwn)

Many second-hand B860H boxes on the market are sold as automatic *PlayStation 4 Jailbreak* dongles (PPPwn) based on Armbian 21.08 (Ubuntu 20.04 Focal) modified by scripts such as `STB-Pwn` (a fork of Stooged's `PI-Pwn`).

### Analysis Findings:
- **Access Gap / Web UI**: Port 80 runs Nginx + PHP-FPM without authentication, executing shell commands as `www-data`.
- **Sudoers Privilege**: The seller added a `www-data ALL=(ALL) NOPASSWD: ALL` entry in `/etc/sudoers`.
- **Log Spam & Full Boot Partition**:
  - The `zram1` log partition (50MB) was 100% full from auth.log and monitoring.
  - The FAT32 `/boot` partition (122MB) was 100% full due to `FSCK*.REC` recovery files and random APK files (`MiBi TiVi`, `ROOT TV`, `Yacine TV`).
- **Exploit Process Loop**: `pppwn64` runs non-stop on the `eth0` interface, loading the CPU and causing heat.

### Cleanup Procedure:
```bash
# 1. Stop services and kill exploit processes
systemctl stop pipwn pppoe dtlink nginx php7.4-fpm dnsmasq
killall -9 pppwn64 pppwn7 pppwn11 timeout
systemctl disable pipwn pppoe dtlink nginx php7.4-fpm dnsmasq
rm -f /etc/systemd/system/pipwn.service /etc/systemd/system/pppoe.service /etc/systemd/system/dtlink.service
systemctl daemon-reload

# 2. Remove PPPwn leftovers and clean rc.local
rm -rf /boot/firmware/PPPwn /media/pwndrives /etc/udev/rules.d/99-pwnmnt.rules
sed -i '/PPPwn/d' /etc/rc.local
sed -i '/devboot.sh/d' /etc/rc.local

# 3. Restore sudoers and flush iptables
sed -i '/www-data.*ALL/d' /etc/sudoers
iptables -P INPUT ACCEPT && iptables -P FORWARD ACCEPT && iptables -P OUTPUT ACCEPT
iptables -t nat -F && iptables -t mangle -F && iptables -F && iptables -X

# 4. Clean junk files from the /boot partition
rm -f /boot/*.apk /boot/*.dpkg-bak /boot/FSCK*.REC
rm -rf /boot/LOST.DIR /boot/Android /boot/firmware
```

---

## 2. Image Selection & Modern MicroSD Preparation (Kernel 6.12 LTS)

To run modern Linux, use the tested build from the **Ophub Amlogic** project:
- **Official Image**: `Armbian_26.11.0_amlogic_s905x-b860h_bookworm_6.12.112_server_2026.10.15.img.gz` (Debian 12 Bookworm, Kernel 6.12.112 LTS).
- **Download Tool**: `tools/download_image.sh` (downloads + decompresses to `Armbian_b860h.img` in the current directory, or a directory you pass).
- **Windows Flashing Tool**: `tools/flash_sd.py` (writes directly to the raw block `\\.\PhysicalDriveX` using the ctypes kernel32 API).

---

## 3. MicroSD Boot Troubleshooting: Fixing the Initramfs ALERT UUID

### Symptoms:
When the MicroSD card is first booted on the TV box, the U-Boot and kernel boot process succeeds, but the process stalls at the BusyBox prompt with the error:
```text
Begin: Waiting for root file system ... Begin: Running /scripts/local-block ... done.
done.
Gave up waiting for root file system device. Common problems:
 - Boot args (cat /proc/cmdline)
 - Check rootdelay= (did the system wait long enough?)
ALERT! UUID=9eacd393-ef9e-4478-a0dd-9207b7ad1da8 does not exist. Dropping to a shell!

BusyBox v1.37.0 (Ubuntu 1:1.37.0-7ubuntu1) built-in shell (ash)
(initramfs) 
```

### Cause:
The MMC driver (`meson-gx-mmc`) needs 3-5 seconds to detect the MicroSD card slot, but the default Ubuntu/Debian initramfs checks the UUID instantly and gives up immediately (*timeout*).

### Permanent Fix in `uEnv.txt`:
Plug the MicroSD card back into the PC, open the `BOOT` (FAT32) partition, then edit the `APPEND` line in the `uEnv.txt` file:
```text
LINUX=/zImage
INITRD=/uInitrd
FDT=/dtb/amlogic/meson-gxl-s905x-b860h.dtb
APPEND=root=LABEL=ROOTFS rootdelay=10 rootflags=data=writeback rw rootwait rootfstype=ext4 console=ttyAML0,115200n8 console=tty0 no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0 max_loop=128 cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory swapaccount=1 video=HDMI-A-1:1920x1080@60e plymouth.enable=0
```
- **`root=LABEL=ROOTFS`**: Looks up the ext4 partition label directly without relying on delayed udev UUID resolution.
- **`rootdelay=10`**: Provides a full 10-second delay so the SD card controller initializes completely.

---

## 4. Migrating the System to Internal eMMC (`armbian-install`)

After booting from MicroSD succeeds and is reachable via SSH:

1. Run the eMMC installation script:
   ```bash
   sudo armbian-install
   ```
2. Enter the following parameters when prompted:
   - **Box ID**: Enter `106` (ZTE B860H model, `s905x` SoC, `meson-gxl-s905x-b860h.dtb` DTB).
   - **Root Filesystem**: Enter `1` (`ext4`).
3. The script automatically:
   - Backs up the original eMMC bootloader to `/usr/lib/u-boot/mybox-bootloader.img`.
   - Repartitions the internal eMMC into a spacious **512 MB** boot partition (`BOOT_EMMC`) and the remaining **6.1 GB** for root (`ROOTFS_EMMC`).
   - Copies the bootloader and kernel, and rsyncs the entire rootfs files to eMMC.

---

## 5. Zero-Wear eMMC Architecture & Tiered Virtual RAM (ZRAM + Swapfile)

Because the internal eMMC chip has limited *write endurance* cycles and is critical to the boot process, the memory and logging architecture is designed to **minimize writes to eMMC to near 0%**:

1. **Level 1: ZRAM Virtual Memory with ZSTD Compression (Priority 100)**:
   - Allocation: **1.8 GB ZRAM (`/dev/zram0`)** compressed directly inside physical RAM using the modern **`zstd`** algorithm (`PRIO 100`).
   - The ZSTD compression ratio ranges from 2.5x to 3.2x, multiplying the 2GB RAM capacity into the equivalent of **~4.5 GB of instant virtual RAM** with 0ms latency and **zero flash wear (zero flash writes)**.
2. **Level 2: 4 GB Emergency Swapfile on MicroSD (Priority -2)**:
   - The swap file is allocated at **4 GB on the MicroSD card** (`/mnt/storage/swapfile`).
   - It has low priority (`PRIO -2`), so it is only touched as an emergency *safety net* if memory load exceeds 4.5 GB. The internal eMMC stays 100% safe.
3. **Zero-Wear Logging (`armbian-ramlog` in `/var/log`)**:
   - The `/var/log` directory is mounted to a compressed ZRAM RAM buffer (`/dev/zram1`).
   - All periodic log writes from the systemd journal, daemons, kernel, and containers happen purely in RAM, eliminating 99% of random writes to eMMC.
   - On a clean shutdown, logs are synced to **`/mnt/storage/log`** on the MicroSD card (not eMMC).
4. **Multi-Gen LRU (MGLRU) & Kernel Sysctl**:
   - File `/etc/sysctl.d/99-server-opt.conf`:
     ```ini
     vm.swappiness = 60
     vm.vfs_cache_pressure = 50
     vm.dirty_background_ratio = 5
     vm.dirty_ratio = 10
     vm.dirty_writeback_centisecs = 6000
     ```
     Holds dirty page writes in RAM for up to 60 seconds before flushing them to disk in a single batch, reducing eMMC flash wear.
---

## 6. Configuring MicroSD as Permanent Internal Storage

So the STB automatically boots from the internal eMMC and the 32GB MicroSD card functions as an internal data storage drive:

### Execution Steps:
1. After the eMMC migration finishes, power off the STB (`poweroff`).
2. Remove the MicroSD card, then power on the STB. The STB will boot Armbian 6.12 directly from the internal eMMC.
3. After logging in via SSH on eMMC, **reinsert the MicroSD card** into the STB slot.
4. Run the internal storage formatting script:
   ```bash
   sudo /root/setup_sd_storage.sh
   ```
   *(Or run the following commands manually)*:
   ```bash
   parted -s /dev/mmcblk1 mklabel msdos
   parted -s /dev/mmcblk1 mkpart primary ext4 1MiB 100%
   mkfs.ext4 -F -q -L "SD_STORAGE" /dev/mmcblk1p1
   mkdir -p /mnt/storage
   mount /dev/mmcblk1p1 /mnt/storage
   chown -R <user>:<user> /mnt/storage
   chmod 775 /mnt/storage
   ```
5. The `/etc/fstab` file on eMMC already binds the `SD_STORAGE` label automatically:
   ```text
   LABEL=SD_STORAGE /mnt/storage ext4 defaults,noatime,nodiratime,nofail 0 2
   ```
6. **Total eMMC-to-MicroSD Offload Architecture (Bind-Mount & Docker)**:
   So the 6.0 GB internal eMMC never fills up with caches, code, repositories, and Docker containers:
   - **`/home/<user>` bound to MicroSD**:
     ```text
     /mnt/storage/home_<user> /home/<user> none defaults,bind,nofail 0 0
     ```
     All user files, pip/npm caches, VS Code workspaces, and git repositories are automatically stored directly on the 30 GB MicroSD card.
   - **`/opt` bound to MicroSD**:
     ```text
     /mnt/storage/opt /opt none defaults,bind,nofail 0 0
     ```
   - **Docker Root Dir isolated on MicroSD (`/etc/docker/daemon.json`)**:
     ```json
     {
       "data-root": "/mnt/storage/docker",
       "log-driver": "json-file",
       "log-opts": {
         "max-size": "10m",
         "max-file": "3"
       }
     }
     ```
     All Docker images, container layers, and volumes automatically live on the MicroSD card. The `<user>` account has been added to the `docker` group so it can run `docker run` without `sudo`.
   - **Systemd Log Limit (`/etc/systemd/journald.conf.d/00-cap-size.conf`)**:
     System log size is capped at a maximum of `50M` so it does not consume eMMC space.
---

## 7. Wi-Fi Driver Fix & Auto-Patching (RTL8189FS) & Bluetooth on Kernel 6.x

### A. Technical Root Cause of the RTL8189FS Wi-Fi Issue:
1. **Out-of-tree Realtek Driver**: Realtek never merged the `8189fs` module into the official Linux kernel source tree (kernel.org), so modern upstream Linux 6.x kernels do not include this module by default.
2. **Linux 6.12 API Change (`set_monitor_channel`)**:
   Kernel 6.12 changed the `set_monitor_channel` callback signature in `cfg80211_ops` by adding a `struct net_device *dev` parameter. The old driver fails to compile with an `incompatible-pointer-types` error.
3. **GCC 12 vs 15 Toolchain Mismatch**:
   The Ophub kernel was built with the GCC 15 toolchain, which includes the `-fmin-function-alignment=4` flag and a `modpost` binary linked against GLIBC 2.38. On Debian 12 Bookworm (GCC 12 & GLIBC 2.36), this flag must be replaced with `-falign-functions=4` and `modpost` must be natively recompiled.

### B. Root Cause of the B860H Bluetooth Issue:
1. The ZTE B860H STB has a pure Wi-Fi chip (RTL8189FS with no integrated Bluetooth).
2. The stock Amlogic P212 / B860H device tree enables a Broadcom phantom node (`compatible = "brcm,bcm43438-bt"`) on UART `serial@84c0`.
3. As a result, on every boot the kernel tries to contact a Broadcom chip that does not exist, triggering a `-110` timeout and stalling boot for 15 seconds.
4. **Fix**: Disable that phantom node in the DTB (`status = "disabled";`), cutting STB boot time to just **12 seconds**! If you need Bluetooth, simply plug in a standard USB Bluetooth dongle fully supported by `btusb`.

### C. Using the Turnkey Auto-Patch:
Run the script we prepared on the STB:
```bash
sudo /root/auto_patch_wifi_bt.sh
```
This script automatically:
- Downloads and installs the 6.12.112 kernel headers from the Ophub repository.
- Fixes the Makefile flag and natively compiles `modpost`.
- Downloads, patches for the Linux 6.12 API, and compiles the `8189fs.ko` module.
- Installs the driver to `/lib/modules/$(uname -r)/...` and enables auto-load in `/etc/modules`.
- Decompiles and disables the Broadcom ghost node in the eMMC DTB.

---

## 8. Tailscale Integration & Passwordless Windows SSH

The STB is connected to the private Tailscale VPN mesh (`<your-tailnet>.ts.net`) and configured for ed25519 key-based SSH authentication without a password:

### A. STB Access IPs:
- **Wired LAN (`eth0`)**: `<STB-LAN-IP>` (e.g. `192.168.1.100`)
- **Backup Wi-Fi (`wlan0`)**: `<STB-WIFI-IP>`
- **Tailscale VPN**: `<TAILSCALE-IP>`

### B. Windows SSH Shortcuts (`~/.ssh/config`):
```ssh-config
Host stb stb-local stb-lan
    HostName <STB-LAN-IP>
    User <user>
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking accept-new

Host stb-wifi
    HostName <STB-WIFI-IP>
    User <user>
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking accept-new

Host stb-ts b860h-ts armbian-ts
    HostName <TAILSCALE-IP>
    User <user>
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking accept-new
```

You can now remote directly into the STB from a Windows terminal/PowerShell without typing a password at all:
```bash
ssh stb       # Access via wired LAN (<STB-LAN-IP>)
ssh stb-wifi  # Access via backup Wi-Fi (<STB-WIFI-IP>)
ssh stb-ts    # Access from anywhere outside the home via Tailscale (<TAILSCALE-IP>)
```

---

## 9. Repository Automation & Diagnostic Scripts

| File | Function |
| :--- | :--- |
| **`tools/auto_patch_wifi_bt.sh`** | Auto-compiler and installer for the RTL8189FS Wi-Fi driver and DTB Bluetooth cleaner for Kernel 6.x. |
| **`tools/diagnostics/ssh_check.sh`** | Native SSH remote diagnostic suite (Kernel, RAM, Swap, Temperature, Uptime, Wi-Fi, Storage Layout, Systemd). |
| **`tools/diagnostics/*.sh`** | Bash diagnostic scripts: `check_optimizations.sh`, `check_bluetooth.sh`, `reboot_and_check.sh`, `install_essentials.sh`. |
| **`tools/optimizations/apply_optimizations.sh`** | Automated tuning script for kernel sysctl, TCP BBR, zram, CPU governor, and journald limits via SSH. |
| **`tools/download_image.sh`** | Ophub Armbian image downloader (`curl`) + `.img.gz` decompressor (`gunzip`). |
| **`tools/flash_sd.py`** | Windows direct raw-disk block I/O flasher via the Win32 ctypes API (`\\.\PhysicalDriveX`) — run `python tools/flash_sd.py` as Administrator. |
| **`boot/meson-gxl-s905x-b860h.dtb`** | Official B860H Device Tree for Linux Kernel 6.x. |

---

## 10. Hardware Debugging: B860H TTL Serial UART Pinout

If the STB hits a bootloader problem (black screen / bootloop) or needs low-level monitoring:

![ZTE B860H UART Pinout](assets/b860h_uart_pinout.png)

### `X2` Pin Header Layout (Near the PCB Screw Hole):
- **Top Row**: **`Gnd`** (Ground) $\to$ Connect to USB-TTL **GND**.
- **Bottom Left**: **`Tx`** (STB Transmit) $\to$ Connect to USB-TTL **RXD**.
- **Bottom Right**: **`Rx`** (STB Receive) $\to$ Connect to USB-TTL **TXD**.
- **VCC**: **DO NOT CONNECT** (the STB is already powered by the 12V adapter).

### Real-time Serial Log Monitoring:
```bash
python tools/diagnostics/boot_monitor.py
```
*(Baudrate: `115200`, 8N1, automatically detects each reboot, timestamps + stall verdict. `serial_monitor.py` as the raw tee fallback).*

---

## 11. Troubleshooting & Playbook: eMMC Cold Boot & MicroSD Storage

This chapter documents critical hardware-level findings and the troubleshooting playbook for the dual-storage architecture (**Internal eMMC + MicroSD Storage**) on the ZTE B860H:

### A. Issue 1: Black Screen (*Crash*) Caused by x86 Bootstrap Code on MicroSD
- **Symptoms**: The STB dies/freezes immediately on a pitch-black screen (*blackscreen*) every time the MicroSD card is inserted at power-on.
- **Root Cause**:
  1. The Amlogic S905X hardware BootROM always checks the MicroSD slot (`MMC 0`) before reading eMMC (`MMC 1`).
  2. When the MicroSD card is formatted with the Linux `parted mklabel msdos` command or an ordinary PC partitioning utility, that program writes PC-DOS x86 bootstrap code (`fa b8 00 10...` = x86 machine instructions `CLI; MOV AX, 0x1000`) to bytes 0-445 of MBR sector 0.
  3. Because the S905X BootROM is **ARM64 (Cortex-A53)** based, when the processor tries to execute those x86 bytes, it immediately suffers an *undefined instruction hardware crash* before ever reaching the internal eMMC!
- **Sector 0 Sanitization Fix** (now automatic in `tools/partition_usb_android.py` when preparing Android USB, or manual via Git Bash):
  ```bash
  # Zero bootstrap bytes 0-445, keep the partition table + 0x55AA (X = SD drive, CHECK FIRST!)
  dd if=/dev/zero of=/dev/sdX bs=1 count=446 conv=notrunc
  ```
  After sanitization, the Amlogic BootROM recognizes the MicroSD card as *pure data storage* and jumps straight to the internal eMMC.

---

### B. Issue 2: Black Screen (*Cold Boot Hang*) Caused by Unsaved eMMC NVRAM
- **Symptoms**: The STB reboots fine on a warm reboot (`sudo reboot`), but if the adapter is unplugged and plugged back in (*cold boot*), the STB refuses to boot and the monitor screen stays pitch black.
- **Root Cause**:
  1. The official `armbian-install` script copies system files to the eMMC FAT32 partition (`mmc 1:1`), but **does not update the built-in U-Boot environment variable (`bootcmd`) in the eMMC NVRAM chip (`0x3ee00000`)**.
  2. On a cold boot (RAM empty from zero), U-Boot executes the factory default value:
     ```text
     bootcmd = run storeboot
     storeboot = if imgread kernel boot ${loadaddr}; then bootm ${loadaddr}; fi; run update;
     ```
  3. U-Boot looks for the old Android kernel partition. Since Android was wiped by Armbian, U-Boot fails to read the kernel (`Err imgread ... Fmt unsupported`) and stops at the emergency console prompt:
     ```text
     gxl_p212_v1#
     ```
  Connect a USB TTL serial cable to the `X2` header (115200 baud). At the `gxl_p212_v1#` prompt, run:
  ```bash
  setenv bootcmd "if fatload mmc 1:1 0x1020000 emmc_autoscript; then autoscr 0x1020000; fi; if fatload mmc 0:1 0x1020000 s905_autoscript; then autoscr 0x1020000; fi; run storeboot"
  saveenv
  ```
  The `saveenv` command permanently writes this configuration to the eMMC storage chip (`Writing to MMC(1)... done`). After that, the STB will boot with a 100% standalone bootloader on every *cold boot* and power outage.
  **Final implementation note (this STB)**: the autoscript was rewritten deterministically (explicit `mmc 1:1`, no USB/SD probing, no `saveenv` inside; dual files `emmc_autoscript` + `aml_autoscript` in `/boot`, compiled on the STB via `mkimage`) and `bootcmd` was simplified before saving:
  ```bash
  setenv bootcmd 'fatload mmc 1:1 0x01020000 emmc_autoscript; autoscr 0x01020000'
  saveenv
  ```
  Warning: do not send U-Boot commands containing `${...}` through a string-based SSH tool (variables may be lost before they arrive) — use literals or an interactive/Python serial session.



### C. Issue 3: Offline Wi-Fi Driver & Pre-Built DTB Deployment
To avoid downloading kernel headers (~70MB) and manual compilation on a new STB:
  ```bash
  bash tools/ship_patch.sh stb
  ```
  Wi-Fi becomes active immediately and the Bluetooth phantom node is cleaned up in **< 2 seconds with no internet**.
