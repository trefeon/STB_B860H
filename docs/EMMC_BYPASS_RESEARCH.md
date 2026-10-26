# Full Research: Bypassing a Faulty eMMC on ZTE B860H V1/V2 (Amlogic S905X)

> **Scope**: A complete technical deep-dive covering hardware architecture, the Amlogic BootROM internals, the multi-stage bootloader chain, and all patching required to achieve a fully functional Armbian Linux boot from an SD card when the internal eMMC is permanently dead.

---

## 1. Hardware Architecture

### ZTE ZXV10 B860H V1/V2 Specs

| Component | Detail |
|---|---|
| **SoC** | Amlogic S905X (28nm, quad-core Cortex-A53 @ 1.5 GHz) |
| **GPU** | ARM Mali-450 MP3 |
| **RAM** | 1GB or 2GB DDR3 (batch-dependent) |
| **eMMC** | 8GB internal (the failing component) |
| **SD Slot** | microSD (mmc0) |
| **Wi-Fi** | Realtek RTL8189FS (SDIO, Wi-Fi only — no Bluetooth combo) |
| **Serial Console** | UART at `ttyAML0`, 115200 bps, pads on PCB |
| **CPU Architecture** | ARMv8-A (AArch64 / ARM64) |

### Why the eMMC Dies

The internal eMMC (mmc1) on these units is a BGA-soldered JEDEC 4.5 spec part. Failures are caused by:

- **Wear-out**: eMMC cells have finite write cycles. TV boxes running 24/7 with high-write Android workloads exhaust cells faster than consumer SSDs.
- **Power loss corruption**: Unclean shutdowns corrupt the eMMC's internal firmware, causing it to return errors on all sectors.
- **Physical delamination**: Poor-quality BGA solder joints fail from repeated thermal stress cycles (heat → cool).

When dead, the eMMC does not respond to any MMC commands. The SoC sees a complete timeout on every interaction with `mmc1`.

---

## 2. The Amlogic BootROM: Internals

### The Multi-Stage ARM Trusted Firmware (ATF) Boot Chain

```
Power On
    │
    ▼
 [BL1 / BootROM] — Read-only code inside the SoC die itself.
    │               Hardcoded. Immutable. Cannot be modified after manufacturing.
    │               Initializes CPU clocks, basic DRAM.
    │               Scans boot device based on POC (Power-On Config) pins.
    ▼
 [BL2] — Trusted Boot Firmware (DDR training, RAM calibration).
    │     Loaded by BL1 from the selected boot device.
    ▼
 [BL30/BL31] — Secure Monitor (TrustZone / EL3).
    │            Sets up the Secure World DRAM region (first 16MB).
    │            Establishes PSCI, SMC call handlers.
    │            PERMANENTLY occupies the first ~16MB of DRAM.
    ▼
 [BL33 / U-Boot] — The actual bootloader (non-secure, EL2/EL1).
    │               Loads kernel, initrd, DTB.
    ▼
 [Linux Kernel] — Armbian boots.
```

### Boot Device Priority (Hard-Coded in BootROM)

The Amlogic S905X BootROM has a **fixed, unmodifiable boot sequence**:

```
eMMC (mmc1)  →  NAND  →  SD Card (mmc0)  →  USB OTG
```

> **Critical implication**: If the eMMC is physically present but broken and still responding (even erroneously), the BootROM may hang at the eMMC probe and never reach the SD card slot. The SD fallback only triggers on a complete hardware timeout.

### How a Dead eMMC Enables SD Boot

When the eMMC NAND dies completely (no bus response):

1. BootROM sends `CMD0` (GO_IDLE_STATE) to mmc1.
2. eMMC produces no response → hardware bus timeout (~1 second).
3. BootROM advances to the **next device: mmc0 (SD card)**.
4. BootROM reads SD sector 0, looking for a valid Amlogic BL2 signature.
5. Finds our injected `uboot_HG680P-sdboot.bin` → proceeds to boot.

**This is the only window the bypass exploits.**

### Partial Failure: The Worst Case

If the eMMC is **partially dead** (acknowledges CMD0 but fails on data reads), the BootROM may loop indefinitely trying to recover it. In this scenario:

- **Short the eMMC CLK pin to ground** during power-on to prevent bus synchronization, forcing a total non-response.
- **Desolder the eMMC BGA** (definitive, requires hot-air rework station).

---

## 3. Bootloader Architecture: Standard vs. Dead-eMMC

### Standard Boot (Healthy eMMC)

```
SD card  = Armbian OS partitions (BOOT + ROOT)
eMMC     = vendor Android + vendor U-Boot in raw boot sectors

Flow:
BootROM → BL2 from eMMC raw sectors → BL30/31 → BL33 (vendor U-Boot, from eMMC)
Vendor U-Boot → reads aml_autoscript from mmc0:1 (SD BOOT partition)
aml_autoscript → s905_autoscript → extlinux/uEnv.txt → Linux kernel
```

The legacy multiboot `aml_autoscript` (`firmware/legacy/aml_autoscript_multiboot.txt`):

```text
setenv start_mmc_autoscript "if fatload mmc 0 1020000 s905_autoscript; then autoscr 1020000; fi;"
```

### Dead-eMMC Boot (This Project)

```
SD card  = Armbian OS partitions + U-Boot injected in raw sectors
eMMC     = dead

Flow:
BootROM → eMMC timeout → tries mmc0 (SD card)
        → reads BL2/U-Boot from raw SD sectors (injected by patch_uboot.py)
        → BL30/31/33 all from SD card
U-Boot (from SD) → aml_autoscript → uEnv.txt → Linux kernel
```

Key difference: **U-Boot itself must live on the SD card in raw sectors**, not just the OS.

---

## 4. Raw Sector Injection: The U-Boot Bypass Mechanism

### Amlogic SD Card Bootloader Layout

```
Byte offset 0-441:   Amlogic bootstrap code (BL2 jump + SoC init)
Byte offset 442-511: MBR Partition Table + signature 0x55AA  ← NEVER OVERWRITE
Byte offset 512+:    U-Boot body (loaded by the bootstrap)
```

Two `dd` operations are required:

```bash
# Op 1: Bootstrap (bytes 0-441, before MBR partition table)
dd if=firmware/uboot_HG680P-sdboot.bin of=/dev/sdX conv=fsync,notrunc bs=1 count=442

# Op 2: U-Boot body (from byte 512 onward, sector 1+)
dd if=firmware/uboot_HG680P-sdboot.bin of=/dev/sdX conv=fsync,notrunc bs=512 skip=1 seek=1
```

The `conv=notrunc` flag prevents erasing the OS partitions beyond the bootloader region. The partition table at bytes 442-511 is intentionally left intact.

This is automated by [`tools/patch_uboot.py`](../tools/patch_uboot.py) and [`tools/do_dd.sh`](../tools/do_dd.sh).

### Why `uboot_HG680P-sdboot.bin` Works on the B860H

Both devices share the same **Amlogic S905X SoC** and nearly identical board layouts:

- Same CPU, same DDR3 timings
- Same GPIO peripheral mapping
- Same SDIO controller assignments (mmc0 = SD, mmc1 = eMMC)

The HG680P U-Boot binary is used because it was **compiled with Amlogic SD card boot support** — it contains the bootstrap header recognized by the BootROM as a valid external boot image. The OEM B860H U-Boot was compiled for eMMC-only boot and lacks this header.

---

## 5. The Bypass `aml_autoscript`: Cutting the eMMC Dependency

The standard multiboot `aml_autoscript` issues `saveenv` (writes to eMMC NVRAM) and `reboot`, both of which fail with a dead eMMC.

Our replacement (`boot/aml_autoscript.cmd`) skips all eMMC interaction:

```text
mmc dev 0                                    # use mmc0 (SD card), not eMMC
mmc rescan
fatload mmc 0:1 0x1000000 uEnv.txt          # load config to DRAM
env import -t 0x1000000 ${filesize}          # parse variables
setenv bootargs ${APPEND}                    # set kernel cmdline
fatload mmc 0:1 0x11000000 ${LINUX}         # load kernel Image
fatload mmc 0:1 0x15000000 ${INITRD}        # load initrd
fatload mmc 0:1 0x1000000  ${FDT}           # load DTB
fdt addr 0x1000000
booti 0x11000000 0x15000000 0x1000000       # boot (ARM64 Image format)
```

### DRAM Memory Map During Boot

| Address | Content |
|---|---|
| `0x1000000` | `uEnv.txt` (overwritten by DTB) |
| `0x11000000` | Kernel `Image` (~42MB) |
| `0x15000000` | `uInitrd` (~25MB) |

---

## 6. ARM64 Kernel Relocation: The `text_offset` Crash

### The Root Cause

Modern ARM64 Linux kernels (v5.8+) set `text_offset = 0x0` in their binary header (kernel commit `9a706b7`, 2020). This is correct per the ARM64 boot protocol — a compliant bootloader reads the field and handles it.

**However**, the vendor U-Boot (`2015.01-g9fbf537`) on the B860H uses a naive relocation formula:

```c
ulong load_addr = ALIGN(gd->ram_base, 2MB) + image_header.text_offset;
// = ALIGN(0x0, 2MB) + 0x0
// = 0x00000000
```

U-Boot attempts to DMA-copy 42MB of kernel data starting at physical address `0x0`.

### Why Address 0x0 Kills the Board

ARM TrustZone / BL31 permanently marks the physical range `0x0–0x1000000` (first 16MB) as **Secure-World memory**. When Non-Secure U-Boot (running at EL1) writes to `0x0`:

1. The ARM MPU/TrustZone hardware blocks the write.
2. A **Synchronous Data Abort** is raised at EL3.
3. BL31 Secure Monitor handles the fault → issues an immediate SoC reset.

UART output at crash:

```
"Synchronous Abort" handler, ESR 0x96000210
elr: 00000000bf26a3c4 lr : 00000000bf26a3c4
```

ESR `0x96000210` decodes to: EC=`0x25` (Data Abort, current EL), DFSC=`0x10` (Synchronous External Abort from blocked secure access).

### The Fix: Patching the Image Header

ARM64 `Image` header layout:

```
Offset 0x00 (4B): code0 (branch instruction)
Offset 0x04 (4B): code1 (NOP)
Offset 0x08 (8B): text_offset  ← PATCH HERE (little-endian u64)
Offset 0x10 (8B): image_size
Offset 0x18 (8B): flags
...
Offset 0x38 (4B): magic = 0x644D5241 ("ARM\x64")
```

We write `0x0000000001080000` (LE) at offset 8, setting `text_offset = 0x1080000` (16.5MB):

```python
# tools/patch_image_header.py
TEXT_OFFSET_ADDR = 8
NEW_TEXT_OFFSET  = 0x1080000
struct.pack_into('<Q', data, TEXT_OFFSET_ADDR, NEW_TEXT_OFFSET)
```

Result: `load_addr = ALIGN(0, 2MB) + 0x1080000 = 0x01080000` — safely above the 16MB TrustZone boundary.

---

## 7. Wi-Fi DTB Patching: GPIO Pin Mismatch

### The Problem

The generic `meson-gxl-s905x-p212.dtb` declares the SDIO Wi-Fi power sequencer:

```dts
sdio_pwrseq: sdio-pwrseq {
    compatible = "mmc-pwrseq-simple";
    reset-gpios = <&gpio GPIOX_85 GPIO_ACTIVE_LOW>;  /* P212 ref board */
    clocks = <&wifi32k>;
    clock-names = "ext_clock";
};
```

- **P212 reference board**: reset GPIO = pin **85** (`0x55`)
- **ZTE B860H V1/V2**: reset GPIO = pin **76** (`0x4c`)

With pin 85, the kernel drives the wrong GPIO low — the RTL8189FS stays in reset, unreachable on the SDIO bus.

### The Binary Patch

The `reset-gpios` property in the compiled DTB encodes as three big-endian 32-bit words:

```
<phandle>  <pin_index>  <active_flags>
0x00000015  0x00000055  0x00000001    ← Original (pin 85)
0x00000015  0x0000004c  0x00000001    ← Patched  (pin 76)
```

We locate this 12-byte sequence at file offset `28280` and overwrite only the pin byte:

```python
# tools/patch_dtb.py
OLD = b'\x00\x00\x00\x15\x00\x00\x00\x55\x00\x00\x00\x01'
NEW = b'\x00\x00\x00\x15\x00\x00\x00\x4c\x00\x00\x00\x01'
```

> The offset `28280` was found using `tools/diagnostics/find_gpio_offset.py`. It may differ across DTB builds, which is why the dynamic finder script is provided.

---

## 8. Bluetooth: Hardware Absent (Expected Error)

The p212 DTB declares a Broadcom Bluetooth device on `uart_A`. The B860H uses RTL8189FS (Wi-Fi-only). Boot logs:

```
Bluetooth: hci0: command 0xfc18 tx timeout
Bluetooth: hci0: BCM: Reset failed (-110)
```

This is benign — the driver is talking to a non-existent serial port. No configuration change will enable Bluetooth. Use a USB Bluetooth dongle if needed.

---

## 9. Complete Boot Sequence (Dead eMMC)

```
Power On
  ├─ BootROM probes mmc1 (eMMC) → hardware timeout (dead)
  └─ BootROM probes mmc0 (SD card) → finds Amlogic BL2 signature
        ↓
  BL2: DDR3 initialization (uboot_HG680P-sdboot.bin)
  BL30: System Control Processor firmware
  BL31: Secure Monitor (maps 0x0–0x1000000 as TrustZone secure)
  BL33: U-Boot (from SD raw sectors)
        ↓
  U-Boot loads aml_autoscript from SD:BOOT partition
    → loads uEnv.txt (LINUX, INITRD, FDT, APPEND variables)
    → loads kernel Image to 0x11000000
         (text_offset patched: 0x0 → 0x1080000, avoids TrustZone crash)
    → loads uInitrd to 0x15000000
    → loads DTB to 0x1000000
         (GPIO patch: reset-gpios pin 85→76, enables RTL8189FS)
    → booti → hands off to Linux kernel
        ↓
  Linux Kernel 6.x (Armbian)
    → mounts rootfs from UUID in APPEND
    → systemd boots
    → NetworkManager / Wi-Fi enabled (RTL8189FS via GPIO 76)
```

---

## 10. Recovery Checklist

| # | Action | Script |
|---|---|---|
| 1 | Flash Armbian `aml-s9xx-box` image to SD | Rufus / BalenaEtcher |
| 2 | Inject U-Boot into SD raw sectors | `python tools/patch_uboot.py` |
| 3 | Copy `boot/aml_autoscript` to SD BOOT partition root | Manual |
| 4 | Create `uEnv.txt` on SD BOOT partition | See `docs/RESEARCH_AND_RECOVERY_GUIDE.md §6` |
| 5 | Patch kernel `Image`: text_offset 0x0 → 0x1080000 | `python tools/patch_image_header.py` |
| 6 | Patch DTB: Wi-Fi reset GPIO pin 85 → 76 | `python tools/patch_dtb.py` |
| 7 | Connect UART TTL adapter (115200 bps), power on | Hardware |
| 8 | If Wi-Fi hangs: `armbian-config` → revert network defaults | SSH/Serial |

---

## 11. References

- ARM Architecture Reference Manual ARMv8-A — ESR encoding, Synchronous Abort §D1.10
- Linux `Documentation/arm64/booting.rst` — ARM64 Image header, `text_offset` spec
- Linux commit `9a706b7` — "arm64: change TEXT_OFFSET to 0x0" (v5.8, 2020)
- Amlogic S905X Datasheet — BootROM boot device priority, mmc controller register map
- Mainline kernel `arch/arm64/boot/dts/amlogic/meson-gxl-s905x-p212.dts` — reference DTB
- ophub/amlogic-s9xxx-armbian — community Armbian builds for Amlogic STBs [github.com/ophub]
- Armbian Community Forum — "S905X dead eMMC boot from SD" discussion threads
