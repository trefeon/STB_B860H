> Terjemahan Bahasa Indonesia dari ../EMMC_BYPASS_RESEARCH.md (English canonical).
> Kembali ke dokumen Inggris: [EMMC_BYPASS_RESEARCH.md](../EMMC_BYPASS_RESEARCH.md)

# Riset Penuh: Melewati eMMC Rusak pada ZTE B860H V1/V2 (Amlogic S905X)

> **Cakupan**: Kajian teknis mendalam yang mencakup arsitektur perangkat keras, internal BootROM Amlogic, rantai bootloader multi-tahap, dan seluruh patching yang diperlukan untuk mencapai boot Linux Armbian yang berfungsi penuh dari kartu SD ketika eMMC internal mati permanen.

---

## 1. Arsitektur Perangkat Keras

### Spesifikasi ZTE ZXV10 B860H V1/V2

| Komponen | Detail |
|---|---|
| **SoC** | Amlogic S905X (28nm, quad-core Cortex-A53 @ 1,5 GHz) |
| **GPU** | ARM Mali-450 MP3 |
| **RAM** | DDR3 1GB atau 2GB (tergantung batch) |
| **eMMC** | 8GB internal (komponen yang gagal) |
| **Slot SD** | microSD (mmc0) |
| **Wi-Fi** | Realtek RTL8189FS (SDIO, hanya Wi-Fi — tanpa combo Bluetooth) |
| **Konsol Serial** | UART pada `ttyAML0`, 115200 bps, pad pada PCB |
| **Arsitektur CPU** | ARMv8-A (AArch64 / ARM64) |

### Mengapa eMMC Mati

eMMC internal (mmc1) pada unit ini adalah part BGA bersolder berstandar JEDEC 4.5. Kegagalan disebabkan oleh:

- **Aus (wear-out)**: Sel eMMC memiliki siklus tulis terbatas. TV box yang menyala 24/7 dengan beban tulis Android berat menghabiskan sel lebih cepat daripada SSD konsumen.
- **Korupsi akibat mati listrik**: Shutdown yang tidak bersih merusak firmware internal eMMC, menyebabkannya mengembalikan galat pada semua sektor.
- **Delaminasi fisik**: Sambungan solder BGA berkualitas buruk gagal akibat siklus stres termal berulang (panas → dingin).

Saat mati, eMMC tidak merespons perintah MMC apa pun. SoC melihat timeout total pada setiap interaksi dengan `mmc1`.

---

## 2. BootROM Amlogic: Internal

### Rantai Boot ARM Trusted Firmware (ATF) Multi-Tahap

```
Power On
    │
    ▼
 [BL1 / BootROM] — Kode read-only di dalam die SoC itu sendiri.
    │               Dikode-keras. Tidak dapat diubah setelah manufaktur.
    │               Menginisialisasi clock CPU, DRAM dasar.
    │               Memindai perangkat boot berdasar pin POC (Power-On Config).
    ▼
 [BL2] — Firmware Boot Tepercaya (latihan DDR, kalibrasi RAM).
    │     Dimuat oleh BL1 dari perangkat boot terpilih.
    ▼
 [BL30/BL31] — Monitor Aman (TrustZone / EL3).
    │            Menyiapkan wilayah DRAM Secure World (16MB pertama).
    │            Menegakkan PSCI, handler panggilan SMC.
    │            Secara PERMANEN menempati ~16MB DRAM pertama.
    ▼
 [BL33 / U-Boot] — Bootloader aktual (non-secure, EL2/EL1).
    │               Memuat kernel, initrd, DTB.
    ▼
 [Kernel Linux] — Armbian boot.
```

### Prioritas Perangkat Boot (Dikode-Keras pada BootROM)

BootROM Amlogic S905X memiliki **urutan boot tetap yang tidak dapat diubah**:

```
eMMC (mmc1)  →  NAND  →  Kartu SD (mmc0)  →  USB OTG
```

> **Implikasi kritis**: Bila eMMC hadir secara fisik tetapi rusak dan masih merespons (sekalipun keliru), BootROM bisa hang pada probing eMMC dan tidak pernah mencapai slot kartu SD. Fallback SD hanya terpicu pada timeout perangkat keras total.

### Bagaimana eMMC Mati Memungkinkan Boot SD

Ketika NAND eMMC mati total (tanpa respons bus sama sekali):

1. BootROM mengirim `CMD0` (GO_IDLE_STATE) ke mmc1.
2. eMMC tidak menghasilkan respons → timeout bus perangkat keras (~1 detik).
3. BootROM lanjut ke **perangkat berikutnya: mmc0 (kartu SD)**.
4. BootROM membaca sektor SD 0, mencari tanda BL2 Amlogic yang valid.
5. Menemukan `uboot_HG680P-sdboot.bin` hasil suntikan kami → lanjut boot.

**Inilah satu-satunya celah yang dieksploitasi bypass ini.**

### Kasus Terburuk: Mati Sebagian

Bila eMMC **mati sebagian** (mengakui CMD0 tetapi gagal pada baca data), BootROM bisa berloop tanpa henti mencoba memulihkannya. Pada skenario ini:

- **Pendekkan pin CLK eMMC ke ground** saat dinyalakan untuk mencegah sinkronisasi bus, memaksa tanpa-respons total.
- **Desolder BGA eMMC** (definitif, butuh stasiun rework udara panas).

---

## 3. Arsitektur Bootloader: Standar vs eMMC-Mati

### Boot Standar (eMMC Sehat)

```
Kartu SD  = partisi OS Armbian (BOOT + ROOT)
eMMC     = Android vendor + U-Boot vendor pada sektor boot mentah

Alur:
BootROM → BL2 dari sektor mentah eMMC → BL30/31 → BL33 (U-Boot vendor, dari eMMC)
U-Boot vendor → membaca aml_autoscript dari mmc0:1 (partisi BOOT SD)
aml_autoscript → s905_autoscript → extlinux/uEnv.txt → Kernel Linux
```

`aml_autoscript` multiboot lawas (`firmware/legacy/aml_autoscript_multiboot.txt`):

```text
setenv start_mmc_autoscript "if fatload mmc 0 1020000 s905_autoscript; then autoscr 1020000; fi;"
```

### Boot eMMC-Mati (Proyek Ini)

```
Kartu SD  = partisi OS Armbian + U-Boot disuntikkan pada sektor mentah
eMMC     = mati

Alur:
BootROM → timeout eMMC → mencoba mmc0 (kartu SD)
        → membaca BL2/U-Boot dari sektor mentah SD (disuntik patch_uboot.py)
        → BL30/31/33 semuanya dari kartu SD
U-Boot (dari SD) → aml_autoscript → uEnv.txt → Kernel Linux
```

Perbedaan kunci: **U-Boot itu sendiri harus tinggal pada kartu SD di sektor mentah**, bukan hanya OS-nya.

---

## 4. Suntikan Sektor Mentah: Mekanisme Bypass U-Boot

### Tata Letak Bootloader Kartu SD Amlogic

```
Offset byte 0-441:   Kode bootstrap Amlogic (lompatan BL2 + init SoC)
Offset byte 442-511: Tabel Partisi MBR + tanda 0x55AA  ← JANGAN PERNAH TIMPA
Offset byte 512+:    Badan U-Boot (dimuat oleh bootstrap)
```

Dua operasi `dd` diperlukan:

```bash
# Op 1: Bootstrap (byte 0-441, sebelum tabel partisi MBR)
dd if=firmware/uboot_HG680P-sdboot.bin of=/dev/sdX conv=fsync,notrunc bs=1 count=442

# Op 2: Badan U-Boot (dari byte 512 dan seterusnya, sektor 1+)
dd if=firmware/uboot_HG680P-sdboot.bin of=/dev/sdX conv=fsync,notrunc bs=512 skip=1 seek=1
```

Flag `conv=notrunc` mencegah penghapusan partisi OS di luar wilayah bootloader. Tabel partisi pada byte 442-511 sengaja dibiarkan utuh.

Ini diotomasi oleh [`tools/patch_uboot.py`](../../tools/patch_uboot.py) dan [`tools/do_dd.sh`](../../tools/do_dd.sh).

### Mengapa `uboot_HG680P-sdboot.bin` Berfungsi pada B860H

Kedua perangkat memakai **SoC Amlogic S905X** yang sama dan tata letak papan yang hampir identik:

- CPU sama, timing DDR3 sama
- Pemetaan periferal GPIO sama
- Penetapan kontroler SDIO sama (mmc0 = SD, mmc1 = eMMC)

Biner U-Boot HG680P dipakai karena **dikompilasi dengan dukungan boot kartu SD Amlogic** — ia memuat header bootstrap yang dikenali BootROM sebagai image boot eksternal yang valid. U-Boot OEM B860H dikompilasi hanya untuk boot-eMMC dan tidak memiliki header ini.

---

## 5. `aml_autoscript` Bypass: Memutus Dependensi eMMC

`aml_autoscript` multiboot standar menerbitkan `saveenv` (menulis ke NVRAM eMMC) dan `reboot`, yang keduanya gagal pada eMMC mati.

Pengganti kami (`boot/aml_autoscript.cmd`) melewatkan semua interaksi eMMC:

```text
mmc dev 0                                    # pakai mmc0 (kartu SD), bukan eMMC
mmc rescan
fatload mmc 0:1 0x1000000 uEnv.txt          # muat config ke DRAM
env import -t 0x1000000 ${filesize}          # urai variabel
setenv bootargs ${APPEND}                    # set cmdline kernel
fatload mmc 0:1 0x11000000 ${LINUX}         # muat kernel Image
fatload mmc 0:1 0x15000000 ${INITRD}        # muat initrd
fatload mmc 0:1 0x1000000  ${FDT}           # muat DTB
fdt addr 0x1000000
booti 0x11000000 0x15000000 0x1000000       # boot (format Image ARM64)
```

### Peta Memori DRAM Selama Boot

| Alamat | Isi |
|---|---|
| `0x1000000` | `uEnv.txt` (ditimpa oleh DTB) |
| `0x11000000` | Kernel `Image` (~42MB) |
| `0x15000000` | `uInitrd` (~25MB) |

---

## 6. Relokasi Kernel ARM64: Crash `text_offset`

### Akar Masalah

Kernel Linux ARM64 mainline (v5.8+) mengatur `text_offset = 0x0` pada header binernya (komit kernel `9a706b7`, 2020). Ini benar menurut protokol boot ARM64 — bootloader yang patuh membaca medan tersebut dan menanganinya.

**Namun**, U-Boot vendor (`2015.01-g9fbf537`) pada B860H memakai rumus relokasi naif:

```c
ulong load_addr = ALIGN(gd->ram_base, 2MB) + image_header.text_offset;
// = ALIGN(0x0, 2MB) + 0x0
// = 0x00000000
```

U-Boot mencoba menyalin-DMA 42MB data kernel mulai dari alamat fisik `0x0`.

### Mengapa Alamat 0x0 Membunuh Papan

ARM TrustZone / BL31 menandai rentang fisik `0x0–0x1000000` (16MB pertama) secara permanen sebagai **memori Secure-World**. Ketika U-Boot Non-Secure (berjalan pada EL1) menulis ke `0x0`:

1. MPU/TrustZone ARM perangkat keras memblokir tulis.
2. **Data Abort Sinkron** dimunculkan pada EL3.
3. Secure Monitor BL31 menangani fault → menerbitkan reset SoC seketika.

Output UART saat crash:

```
"Synchronous Abort" handler, ESR 0x96000210
elr: 00000000bf26a3c4 lr : 00000000bf26a3c4
```

ESR `0x96000210` terdekode: EC=`0x25` (Data Abort, EL saat ini), DFSC=`0x10` (Synchronous External Abort dari akses secure yang diblokir).

### Perbaikan: Menambal Header Image

Tata header `Image` ARM64:

```
Offset 0x00 (4B): code0 (instruksi branch)
Offset 0x04 (4B): code1 (NOP)
Offset 0x08 (8B): text_offset  ← PATCH DI SINI (u64 little-endian)
Offset 0x10 (8B): image_size
Offset 0x18 (8B): flags
...
Offset 0x38 (4B): magic = 0x644D5241 ("ARM\x64")
```

Kami menulis `0x0000000001080000` (LE) pada offset 8, mengatur `text_offset = 0x1080000` (16,5MB):

```python
# tools/patch_image_header.py
TEXT_OFFSET_ADDR = 8
NEW_TEXT_OFFSET  = 0x1080000
struct.pack_into('<Q', data, TEXT_OFFSET_ADDR, NEW_TEXT_OFFSET)
```

Hasil: `load_addr = ALIGN(0, 2MB) + 0x1080000 = 0x01080000` — aman di atas batas TrustZone 16MB.

---

## 7. Patching DTB Wi-Fi: Ketidakcocokan Pin GPIO

### Masalah

`meson-gxl-s905x-p212.dtb` generik mendeklarasikan power sequencer Wi-Fi SDIO:

```dts
sdio_pwrseq: sdio-pwrseq {
    compatible = "mmc-pwrseq-simple";
    reset-gpios = <&gpio GPIOX_85 GPIO_ACTIVE_LOW>;  /* papan ref P212 */
    clocks = <&wifi32k>;
    clock-names = "ext_clock";
};
```

- **Papan referensi P212**: reset GPIO = pin **85** (`0x55`)
- **ZTE B860H V1/V2**: reset GPIO = pin **76** (`0x4c`)

Dengan pin 85, kernel menarik GPIO yang salah ke rendah — RTL8189FS tetap dalam reset, tak terjangkau pada bus SDIO.

### Patch Biner

Properti `reset-gpios` pada DTB terkompilasi dienkode sebagai tiga word 32-bit big-endian:

```
<phandle>  <pin_index>  <active_flags>
0x00000015  0x00000055  0x00000001    ← Asli (pin 85)
0x00000015  0x0000004c  0x00000001    ← Dipatch  (pin 76)
```

Kami menemukan sekuens 12-byte ini pada offset berkas `28280` dan menimpa hanya byte pin-nya:

```python
# tools/patch_dtb.py
OLD = b'\x00\x00\x00\x15\x00\x00\x00\x55\x00\x00\x00\x01'
NEW = b'\x00\x00\x00\x15\x00\x00\x00\x4c\x00\x00\x00\x01'
```

> Offset `28280` ditemukan memakai `tools/diagnostics/find_gpio_offset.py`. Ia dapat berbeda antar build DTB, sehingga skrip pencari dinamis disediakan.

---

## 8. Bluetooth: Perangkat Keras Absen (Galat yang Wajar)

DTB p212 mendeklarasikan perangkat Bluetooth Broadcom pada `uart_A`. B860H memakai RTL8189FS (hanya Wi-Fi). Log boot:

```
Bluetooth: hci0: command 0xfc18 tx timeout
Bluetooth: hci0: BCM: Reset failed (-110)
```

Ini jinak — driver berbicara ke port serial yang tidak ada. Tidak ada perubahan konfigurasi yang mengaktifkan Bluetooth. Gunakan dongle Bluetooth USB bila perlu.

---

## 9. Urutan Boot Lengkap (eMMC Mati)

```
Power On
  ├─ BootROM memprobe mmc1 (eMMC) → timeout perangkat keras (mati)
  └─ BootROM memprobe mmc0 (kartu SD) → menemukan tanda BL2 Amlogic
        ↓
  BL2: inisialisasi DDR3 (uboot_HG680P-sdboot.bin)
  BL30: firmware System Control Processor
  BL31: Secure Monitor (memetakan 0x0–0x1000000 sebagai TrustZone secure)
  BL33: U-Boot (dari sektor mentah SD)
        ↓
  U-Boot memuat aml_autoscript dari partisi SD:BOOT
    → memuat uEnv.txt (variabel LINUX, INITRD, FDT, APPEND)
    → memuat kernel Image ke 0x11000000
         (text_offset dipatch: 0x0 → 0x1080000, menghindari crash TrustZone)
    → memuat uInitrd ke 0x15000000
    → memuat DTB ke 0x1000000
         (patch GPIO: reset-gpios pin 85→76, mengaktifkan RTL8189FS)
    → booti → serah terima ke kernel Linux
        ↓
  Kernel Linux 6.x (Armbian)
    → me-mount rootfs dari UUID pada APPEND
    → systemd boot
    → NetworkManager / Wi-Fi aktif (RTL8189FS via GPIO 76)
```

---

## 10. Daftar Periksa Pemulihan

| # | Aksi | Skrip |
|---|---|---|
| 1 | Flash image Armbian `aml-s9xx-box` ke SD | Rufus / BalenaEtcher |
| 2 | Suntikkan U-Boot ke sektor mentah SD | `python tools/patch_uboot.py` |
| 3 | Salin `boot/aml_autoscript` ke akar partisi BOOT SD | Manual |
| 4 | Buat `uEnv.txt` pada partisi BOOT SD | Lihat `docs/RESEARCH_AND_RECOVERY_GUIDE.md §6` |
| 5 | Patch kernel `Image`: text_offset 0x0 → 0x1080000 | `python tools/patch_image_header.py` |
| 6 | Patch DTB: pin reset GPIO Wi-Fi 85 → 76 | `python tools/patch_dtb.py` |
| 7 | Sambungkan adapter UART TTL (115200 bps), nyalakan | Perangkat keras |
| 8 | Bila Wi-Fi hang: `armbian-config` → kembalikan default jaringan | SSH/Serial |

---

## 11. Referensi

- ARM Architecture Reference Manual ARMv8-A — Enkode ESR, Synchronous Abort §D1.10
- Linux `Documentation/arm64/booting.rst` — Header Image ARM64, spesifikasi `text_offset`
- Komit Linux `9a706b7` — "arm64: change TEXT_OFFSET to 0x0" (v5.8, 2020)
- Datasheet Amlogic S905X — Prioritas perangkat boot BootROM, peta register kontroler mmc
- Device tree mainline `arch/arm64/boot/dts/amlogic/meson-gxl-s905x-p212.dts` — DTB referensi
- ophub/amlogic-s9xxx-armbian — build Armbian komunitas untuk STB Amlogic [github.com/ophub]
- Forum Komunitas Armbian — thread diskusi "S905X dead eMMC boot from SD"
