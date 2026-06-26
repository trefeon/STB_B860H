# ZTE ZXV10 B860H V1/V2 (Amlogic S905X) Research & Recovery Guide
This document serves as a complete technical guide and reference for booting Armbian Linux (Kernel 6.x+) on a ZTE B860H V1/V2 TV box with a **dead internal eMMC** by bypassing the storage controller and booting directly from a MicroSD card.

---

## 1. Hardware Architecture & The Dead eMMC Issue

### Hardware Specs (ZTE B860H V1/V2)
* **SoC**: Amlogic S905X (Quad-core ARM Cortex-A53)
* **GPU**: ARM Mali-450 MP
* **RAM**: 1GB / 2GB DDR3 (depending on batch)
* **Storage Interface**: 
  * `mmc0`: MicroSD card controller
  * `mmc1`: Onboard eMMC storage controller
* **Wireless Chipset**: Realtek RTL8189FS (Wi-Fi-only, SDIO interface)

### Symptom of Dead eMMC
When the internal eMMC fails permanently:
1. Low-level kernel logs show `mmc1: Failed to initialize a non-removable card` or continuous I/O errors.
2. The standard Amlogic bootloader chain (stored in internal eMMC boot partitions) is unreadable, causing the device to hang in a boot loop or show no serial output at all.
3. The board must be configured to run U-Boot entirely from the SD card.

---

## 2. Bootloader Bypass: Raw Sector Injection

Amlogic SoCs have a hardcoded ROM bootloader (BL1) that scans boot media for a valid bootloader signature (BL2) in a specific sector layout. For MicroSD cards, it reads the start of the disk.

### MBR Partition Protection
To make the SD card bootable while keeping its partitions intact, we must write a custom U-Boot binary (`uboot_HG680P.bin`) to the Master Boot Record (Sector 0) and the sectors immediately following it. However, we must **never overwrite the MBR partition table** (bytes 442 to 511 in sector 0), otherwise the partition boundaries will be lost, corrupting the FAT and ext4 partitions.

### The DD Injection Scheme
The injection is divided into two operations:
1. **Bootstrap Code**: Write the first 442 bytes of U-Boot to sector 0 (bytes 0–441). This contains the initial boot instructions for the Amlogic ROM.
2. **U-Boot Body**: Write the rest of U-Boot from byte 512 onward directly to sector 1 of the SD card.

```
       Sector 0 (512 Bytes)                            Sector 1+
+----------------------+----------+---------+   +------------------------------+
| Bootstrap (0-441 B)  | MBR (70B)|Sig (55AA|   |      U-Boot Body (512 B+)    |
+----------------------+----------+---------+   +------------------------------+
| <-- Written (dd 1)-->| Kept Intact        |   | <-- Written (dd 2) --------->|
```

In python, this is implemented in [patch_uboot.py](file:///d:/STB_B860H/patch_uboot.py):
```python
# Write bootstrap code
img.seek(0)
img.write(uboot_data[:442])

# Write U-Boot body (skipping MBR table)
img.seek(512)
img.write(uboot_data[512:])
```

---

## 3. Kernel Relocation Fix: The `text_offset` Crash

Modern mainline ARM64 Linux kernels (v5.8+) default to a kernel text offset of `0` in their image header. Older, vendor-supplied U-Boot bootloaders (like the S905X vendor U-Boot v2015.01) calculate the kernel relocation address using:
$$\text{relocated\_addr} = \text{ALIGN}(\text{gd->ram\_base}, \text{2MB}) + \text{text\_offset}$$

Since $\text{gd->ram\_base}$ is `0x00000000` and $\text{text\_offset}$ is `0`, U-Boot attempts to write the kernel directly to physical address `0x00000000`.

### The Crash Mechanism
The first 16MB of DRAM on these TV boxes is protected secure memory reserved for the TrustZone / Secure Monitor (BL30/31/32). Writing to `0x0` triggers a hardware-level `Synchronous Abort` exception (ESR `0x96000210`), resulting in an immediate crash and reboot.

### The Header Patch Fix
We patch the kernel image file (`/Image` on the FAT32 boot partition) by modifying its header fields to offset the load address to a safe writable DRAM region:
* **Byte Offset**: `8` (represents the `text_offset` field, a 64-bit little-endian integer).
* **Patch Value**: `0x1080000` (16.5 MB).
* **Hex String**: `00 00 08 01 00 00 00 00`

Once patched, U-Boot relocates the kernel to `0x01080000`, bypassing the secure memory region and allowing the kernel to boot normally. This is implemented in [patch_image_header.py](file:///d:/STB_B860H/patch_image_header.py).

---

## 4. Internal Wi-Fi Device Tree Patching

Mainline Linux device tree blobs (like `meson-gxl-s905x-p212.dtb`) are written for reference boards. The generic `p212` design maps the SDIO Wi-Fi power sequencer's (`sdio-pwrseq`) reset pin to GPIO Pin 85.

### GPIO Pin Mapping Discrepancy
* **Reference `p212` Board**: Wi-Fi reset GPIO pin = `85` (`0x55`)
* **ZTE B860H Board Layout**: Wi-Fi reset GPIO pin = `76` (`0x4c`)

Because the kernel was pulling Pin 85 low to reset the Wi-Fi chip, the physical Wi-Fi module on the B860H board remained in a low-power reset state, failing to respond on the SDIO bus.

### The DTB Patch Fix
We patch the compiled DTB (`/dtb/amlogic/meson-gxl-s905x-p212.dtb`) to change the pin mapping from 85 to 76 in-place.
* **Property Node**: `sdio-pwrseq` -> `reset-gpios`
* **Target Bytes**: The GPIO entry format is `<phandle pin_index flags>`. In hex:
  * **Original**: `00 00 00 15 00 00 00 55 00 00 00 01` (Pin 85 / `0x55`)
  * **Patched**: `00 00 00 15 00 00 00 4c 00 00 00 01` (Pin 76 / `0x4c`)
* **File Offset**: `28280` (may vary depending on DTB build, but can be located dynamically by searching for the byte sequence).

This is implemented in [patch_dtb.py](file:///d:/STB_B860H/patch_dtb.py).

---

## 5. Bluetooth Diagnostic Findings & Limitations

On boot, the kernel reports errors trying to talk to a Broadcom Bluetooth controller:
```
[   13.669504] Bluetooth: hci0: command 0xfc18 tx timeout
[   13.669504] Bluetooth: hci0: BCM: failed to write update baudrate (-110)
[   13.675650] Bluetooth: hci0: Failed to set baudrate
[   15.684236] Bluetooth: hci0: command 0xfc18 tx timeout
[   15.685323] Bluetooth: hci0: BCM: Reset failed (-110)
```

### Explaining the Error
1. **Device Tree Declaration**: The generic `p212` DTB declares a Broadcom Bluetooth device (`brcm,bcm43438-bt` or similar) connected to serial interface `uart_A` (`/dev/ttyS1`).
2. **Missing Hardware**: This specific revision of the B860H uses the **RTL8189FS** Wi-Fi chip. Unlike the combo chips (e.g. AP6212), the RTL8189FS is a **Wi-Fi-only** module. There is no physical Broadcom Bluetooth chip on the board.
3. **Timeout (-110)**: The kernel driver sends commands to the serial port expecting a Broadcom chip response. Since no chip is present, the transaction times out (`-110`), resulting in the "Reset failed" message.

### Resolution
* No configuration changes can enable onboard Bluetooth because the hardware is physically absent.
* **Workaround**: Install a standard USB Bluetooth dongle. The mainline kernel contains drivers for common USB Bluetooth chipsets, making them plug-and-play.

---

## 6. Full Recovery Runbook

Follow these exact steps if your SD card becomes corrupted or you need to build a new one from scratch:

### Step 1: Prepare and Flash the SD Card
1. Download a modern mainline Armbian minimal/server image for `aml-s9xx-box` (e.g., Debian Trixie or Ubuntu Noble).
2. Flash it to a high-quality MicroSD card using Rufus or BalenaEtcher.
3. Decompress the `.img.xz` file first if writing via scripts.

### Step 2: Inject the Custom Bootloader
1. Run [patch_uboot.py](file:///d:/STB_B860H/patch_uboot.py) (or `do_dd.sh`) targeting the output image file or the raw SD card drive letter. This injects `uboot_HG680P.bin` while keeping the partition table safe.

### Step 3: Configure `uEnv.txt` & Copy Autoscript
Mount the `BOOT` partition of the SD card:
1. Copy `aml_autoscript` to the root directory of the `BOOT` partition.
2. Create `uEnv.txt` in the root of the `BOOT` partition:
   ```ini
   LINUX=Image
   INITRD=uInitrd
   FDT=dtb/amlogic/meson-gxl-s905x-p212.dtb
   APPEND=root=UUID=<YOUR-ROOTFS-UUID> rootflags=data=writeback console=ttyAML0,115200n8 console=tty0 rw no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0 splash plymouth.ignore-serial-consoles
   ```
   *(Retrieve the UUID of the second partition of your flashed SD card using `blkid` in Linux or partition managers in Windows).*

### Step 4: Apply Patches to Boot Files
Run the following helper scripts to patch the files directly on the mounted SD card partition:
1. Run [patch_image_header.py](file:///d:/STB_B860H/patch_image_header.py) to set the text offset of `BOOT:\Image` to `0x1080000`.
2. Run [patch_dtb.py](file:///d:/STB_B860H/patch_dtb.py) to modify the Wi-Fi reset GPIO pin in `BOOT:\dtb\amlogic\meson-gxl-s905x-p212.dtb` to pin `76`.

### Step 5: Boot and Resolve First-Boot Wi-Fi Hangs
1. Insert the SD card into the TV box and power it on.
2. If Wi-Fi scanning hangs during initial setup:
   * Run `sudo armbian-config`.
   * Go to **Network** -> **Advanced Network Configuration** -> **Revert to defaults**.
   * Restart network services: `sudo systemctl restart NetworkManager`.
