# Armbian Toolkit & Installation Guide for ZTE ZXV10 B860H V1/V2 (Amlogic S905X)

> Documentation in English is canonical. Terjemahan Bahasa Indonesia: [docs/id/README.id.md](docs/id/README.id.md) · [Indeks Indonesia](docs/id/INDEX.id.md).
> Audience: B860H owners installing Armbian — start with the guides below.

This repository contains technical guides, investigations, automation scripts, and diagnostic tools for running **Armbian Linux** on the **ZTE ZXV10 B860H** STB, covering two main scenarios:

1. **Healthy / Fresh eMMC**: Modern Armbian installation guide (**Debian 12 Bookworm / Linux Kernel 6.12.y LTS**), cleanup of marketplace exploit firmware (PPPwn), full migration to internal eMMC, Swap Virtual Memory setup, and reuse of the MicroSD card as permanent internal storage (30 GB).
   👉 **[Read the Complete Modern Armbian 6.x Guide (eMMC & MicroSD)](docs/MODERN_ARMBIAN_6X_INSTALL_GUIDE.md)**

2. **Dead eMMC Device (Dead/Corrupted eMMC Hardware)**: Guide to bypassing the internal eMMC bootloader by injecting U-Boot directly into the MicroSD card raw sectors, kernel relocation patching, and DTB patching.
   👉 **[Read the Dead eMMC Recovery Guide (Legacy Bypass)](docs/PERMANENT_SD_BOOT_GUIDE.md)**

---

## 🚀 Quick Start: Modern Armbian 6.12 LTS on eMMC & SD Storage

For those with a healthy-eMMC B860H STB (including former PPPwn / Android TV units):

1. **Download the Official Image**:
   ```bash
   bash tools/download_image.sh
   ```
   *(Downloads `Armbian_26.11.0_amlogic_s905x-b860h_bookworm_6.12.112_server` and extracts it to `Armbian_b860h.img` in the download directory)*.

2. **Flash to MicroSD**:
   Run `python tools/flash_sd.py` (Run as Administrator) or use BalenaEtcher/Rufus.

3. **Configure `uEnv.txt` on the `BOOT` Partition (Important)**:
   Make sure the `APPEND` line includes `rootdelay=10` and `root=LABEL=ROOTFS`:
   ```ini
   FDT=/dtb/amlogic/meson-gxl-s905x-b860h.dtb
   APPEND=root=LABEL=ROOTFS rootdelay=10 rootflags=data=writeback rw rootwait rootfstype=ext4 console=ttyAML0,115200n8 console=tty0 no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0 max_loop=128 cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory swapaccount=1 video=HDMI-A-1:1920x1080@60e plymouth.enable=0
   ```

4. **Boot MicroSD & Migrate to eMMC**:
   - Insert the MicroSD into the STB and power it on. Log in over SSH (`root` / `1234`).
   - Run `sudo armbian-install` $\to$ enter ID `106` (B860H) $\to$ select `1` (ext4).

5. **Set Up Swap & Repurpose MicroSD as Storage**:
   - Power off the STB (`poweroff`), remove the MicroSD, then power the STB back on (the STB boots from internal eMMC).
   - Reinsert the MicroSD, then run:
     ```bash
     sudo /root/setup_sd_storage.sh
     ```
   - The MicroSD is automatically reformatted to pure `ext4` (label `SD_STORAGE`) and mounted at `/mnt/storage` and `/home/<user>/storage`.

6. **Check System Health via Native SSH & Bash**:
   ```bash
   # Run the diagnostic script (automatic over SSH without a password)
   bash tools/diagnostics/ssh_check.sh

   # Or connect remotely directly via Windows shortcuts
   # (configure HostName values in ~/.ssh/config first):
   ssh stb       # Wired LAN (<STB-LAN-IP>; e.g. 192.168.1.100)
   ssh stb-wifi  # Backup Wi-Fi (<STB-WIFI-IP>)
   ssh stb-ts    # Tailscale VPN (<TAILSCALE-IP>)
   ```

7. **Offline Wi-Fi & DTB Turnkey Auto-Patch Package**:
   For a new STB, run a single command from your PC/laptop with no on-device compilation needed:
   ```bash
   bash tools/ship_patch.sh stb
   ```
   *(Automatically installs the `8189fs.ko` Wi-Fi driver and the `meson-gxl-s905x-b860h.dtb` DTB in < 2 seconds with no internet)*.

8. **Hardware UART Pinout & Cold Boot Recovery**:
   If you run into bootloader / cold boot hang issues, connect a USB TTL adapter to the B860H PCB `X2` header:
   - **Gnd** $\to$ `GND`
   - **Tx** $\to$ `RXD`
   - **Rx** $\to$ `TXD`
   - Run `python tools/diagnostics/boot_monitor.py` (Baudrate: `115200`) — detects every reboot, timestamps it, and reports an automatic hang verdict. `serial_monitor.py` is available as a raw-tee fallback.
   - Full guide: 👉 **[Read Chapter 11 Troubleshooting eMMC & Cold Boot](docs/MODERN_ARMBIAN_6X_INSTALL_GUIDE.md#11-troubleshooting--playbook-emmc-cold-boot--microsd-storage)**
---

## 🛠️ Dead eMMC Bypass Guide (Legacy Hardware Bypass)

*(The following section is for B860H units whose internal eMMC hardware is totally dead).*

---

### Bypass Process Summary

This repository contains documentation, automation scripts, and step-by-step guides for installing and running **Armbian Linux** (Mainline Kernel 6.x) on a **ZTE ZXV10 B860H V1/V2** STB suffering **total internal eMMC hardware failure (dead eMMC)**.

When the internal eMMC is totally dead, the standard boot method (relying on the internal eMMC bootloader to call `u-boot.ext`) will not work. This guide explains how to bypass eMMC entirely by writing the bootloader directly to the SD card raw sectors, patching the kernel header to prevent crashes, and patching the DTB so the internal Wi-Fi works.

---

## 🛠️ Installation Process Summary

The bypass and boot procedure consists of 5 main stages:

```text
[1. Flash Image] ➔ [2. Inject U-Boot into Raw SD] ➔ [3. Patch Kernel Header (Crash Bypass)] ➔ [4. Patch DTB (Enable Wi-Fi)] ➔ [5. Insert & Boot]
```

---

## 🚀 Step 1: Flash Armbian to the SD Card

1. Prepare a MicroSD card (at least 8GB, Class 10 or faster).
2. Download the latest Armbian image for **Amlogic S9xxx Box** (example: `Armbian_community_26.8.0_Aml-s9xx-box_trixie_current_6.18.35_minimal.img.xz`).
3. Flash that image to the SD card using Rufus, BalenaEtcher, or Win32DiskImager.

---

## 💾 Step 2: Inject U-Boot into the SD Card Raw Sectors (Important)

Because the eMMC is dead, the Amlogic SoC must read the bootloader directly from the SD card raw sectors. We must inject U-Boot while preserving the MBR partition table so the SD card stays intact/readable.

We provide automatic scripts to do this:

* **Windows users:** Run the Python script:

  ```bash
  python tools/patch_uboot.py
  ```

  *(This script takes the `uboot_HG680P-sdboot.bin` file in the `firmware/` folder and writes the bootstrap portion to bytes 0-441 plus the U-Boot body starting at byte 512 to your SD card).*

* **Linux / Git Bash users:** Run the shell script:

  ```bash
  ./tools/do_dd.sh
  ```

---

## 📝 Step 3: Boot File Configuration & Kernel Header Patching (Crash Bypass)

After writing U-Boot to the raw sectors, unplug and replug the SD card on your computer so the `BOOT` partition reappears.

### 3A. Copying the Required Boot Files

1. Copy the `aml_autoscript` file from the `boot/` folder to the root of the SD card `BOOT` partition.
2. Create a file named **`uEnv.txt`** at the root of the SD card `BOOT` partition with the following configuration:

   ```ini
   LINUX=Image
   INITRD=uInitrd
   FDT=dtb/amlogic/meson-gxl-s905x-p212.dtb
   APPEND=root=UUID=replace-with-your-rootfs-uuid rootflags=data=writeback console=ttyAML0,115200n8 console=tty0 rw no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0 splash plymouth.ignore-serial-consoles
   ```

### 3B. Patching the Kernel Header (`f:\Image`) for Crash Bypass

* **Problem:** Modern mainline kernels (v5.8+) use a `text_offset` value of `0`. The vendor U-Boot computes the relocation destination address with the formula `ALIGN(start_ram, 2MB) + text_offset = 0 + 0 = 0x0`. Writing the kernel to `0x0` triggers a `Synchronous Abort` hardware exception (ESR `0x96000210`) because that region is protected memory (Secure Monitor / TrustZone).
* **Solution:** Run the helper Python script to patch the `text_offset` value inside the `Image` file to `0x1080000` (16.5 MB):

  ```bash
  python tools/patch_image_header.py
  ```

  *(The script automatically creates an `Image.bak` backup and writes the bytes `00 00 08 01 00 00 00 00` at byte offset 8 of the `Image` file on your SD card. You can also pass a custom path/drive letter as an argument, for example: `python tools/patch_image_header.py g:\Image`).*

---

## 📶 Step 4: Patching the Device Tree (DTB) for B860H Wi-Fi

The stock generic DTB (`meson-gxl-s905x-p212.dtb`) maps the SDIO Wi-Fi reset pin to pin 85. However, the physical board layout of the ZTE B860H maps that reset pin to GPIO pin **76**.

To fix this without breaking mainline kernel compatibility:

1. Run the Python script:

   ```bash
   python tools/patch_dtb.py
   ```

   *(This script patches the `dtb/amlogic/meson-gxl-s905x-p212.dtb` file on the SD card in place at file offset `28280`, changing the reset pin value from `85` (`0x55`) to `76` (`0x4c`). You can also pass a custom DTB file path as an argument, for example: `python tools/patch_dtb.py g:\dtb\amlogic\meson-gxl-s905x-p212.dtb`).*

2. The modern kernel can now power on the Wi-Fi chip automatically and load the correct driver (`brcmfmac` / `rtl8723bs`).

---

## 🔌 Step 5: Connect & Boot

1. Safely eject the SD card (Eject) from your PC.
2. Make sure the STB is powered off, then insert the SD card into the STB MicroSD slot.
3. Connect the Serial TTL cable to your PC and plug in the STB power cable.
4. The device will automatically read `aml_autoscript` from the SD card, avoid the internal memory loop, and boot **Armbian Linux** directly!
5. After the boot process finishes, you will be asked to enter a new root password on the serial monitor:

   ```text
   IP address: Waiting for local connection!
   Create root password:
   ```

6. Enjoy your B860H STB now fully working running a Linux OS directly from the SD card!

---

## 💡 Wi-Fi Tips & Troubleshooting

If Wi-Fi scanning hangs or shows no connection list on first setup:

1. Open the Armbian configuration by running:

   ```bash
   sudo armbian-config
   ```

2. Go to **Network** -> **Advanced Network Configuration**.
3. Select the option to revert the network settings to **Armbian defaults**.
4. Restart the networking service or reboot your STB. Wi-Fi scanning and connection will then run smoothly!

---

## 📂 Repository Structure

This repository is organized with the following clean structure:

* **[`boot/`](boot/)**: Active boot scripts only (`aml_autoscript` + source, `emmc_autoscript` + source).
* **[`firmware/`](firmware/)**: Bootloader binaries (`uboot_B860H-emmc-stock.bin`, `uboot_HG680P-sdboot.bin`), stock reference DTB (`meson-gxl-s905x-p212-stock-unpatched.dtb`), and the legacy unbrick set (`legacy/`).
* **[`tools/`](tools/)**: Contains automation scripts (convention: **bash+ssh** for STB commands, **Python** only for serial-UART/binary-parsing/raw-disk Windows work):
  * `download_image.sh`: Download + extract the Ophub image (`curl` + `gunzip`).
  * `flash_sd.py`, `flash_android_p2.py`, `partition_usb_android.py`, `simg2img.py`: Windows raw-disk / binary-format I/O (no bash equivalent).
  * `tools/vendor/`: Third-party vendor blobs without source (`ampack.exe`, Amlogic image pack/unpack).
  * `patch_uboot.py` / `do_dd.sh`: U-Boot injection into raw sectors (Python with image auto-detection, or `dd` on bash/Linux) — pick one.
  * `patch_dtb.py`, `patch_image_header.py`, `mkimage_script.py`, `find_gpio_offset.py`, `diff_dtb.py`, `read_dtb.py`, `read_header.py`: Binary/DTB utilities (Python, all paths via arguments).
  * `diagnostics/boot_monitor.py`: Primary UART monitor — detects every reboot, timestamps, hang verdict.
  * `diagnostics/test_bootm.py [--image F --bootargs "..."]`: Test `bootm` boot from USB (replacement for test_boot_stock/boot_android_test).
  * `diagnostics/auto_restore_linux.py`, `serial_recovery.py`, `test_chainload_uboot.py`, `uboot_interactive.py`: U-Boot prompt interaction over serial (`<COM-PORT>`, e.g. `COM5` on Windows).
  * `diagnostics/*.sh`, `optimizations/*.sh`, `ship_patch.sh`, `auto_patch_wifi_bt.sh`: SSH auditing, patching, and tuning (bash).
  * `hdmi-console.sh` + `99-hdmi-console.rules`: HDMI console policy on the STB (blank + disable getty when HDMI is unplugged).
  * `hotspot-failover.sh` + `.service`/`.timer`: Emergency AP — brings `B860H-AP` up after 2x failed uplink checks, down when uplink returns (SSH at the AP default `192.168.50.1`).
* **[`packages/`](packages/)**: Deployable bundles — `b860h_patch/` (Armbian Wi-Fi/DTB fix), `android_custom/` (sideload APKs), `stock-roms/` (FWAero/Pulpstone stock Android, on-disk only, git-ignored).
* **[`docs/`](docs/)**: Modern eMMC & MicroSD installation guides, hardware research, and SD recovery guides — start with [`STB_B860H_FULL_SETUP_GUIDE.md`](docs/STB_B860H_FULL_SETUP_GUIDE.md) for this box's exact end-to-end setup.
---

## 🔧 Deterministic Boot (Fix for the `gxl_p212_v1#` Prompt)

The vendor U-Boot (`bootcmd=run storeboot`) has no hook for eMMC scripts — it sometimes boots, sometimes stops at the prompt. Permanent fix (already applied on this STB):

1. `/boot/emmc_autoscript` + `/boot/aml_autoscript` = deterministic script (explicit device `mmc 1:1`, no USB/SD probing, no `saveenv`), compiled **on the STB** via `mkimage`.
2. `setenv bootcmd 'fatload mmc 1:1 0x01020000 emmc_autoscript; autoscr 0x01020000'; saveenv` — boot always goes through the eMMC script.

Note: never send commands containing `${...}` through string-based SSH tools (variables can be lost before arrival). Use literals, or type U-Boot commands via an interactive session/Python serial.

## 🖥 HDMI Console Policy

`tools/hdmi-console.sh` + udev rule (installed at `/usr/local/bin`, `/etc/udev/rules.d/99-hdmi-console.rules`): HDMI connected → unblank + `getty@tty1` on; HDMI unplugged → output blanked + getty off for a lightweight (pure server) load.
