> Terjemahan Bahasa Indonesia dari ../RESEARCH_AND_RECOVERY_GUIDE.md (English canonical).
> Kembali ke dokumen Inggris: [RESEARCH_AND_RECOVERY_GUIDE.md](../RESEARCH_AND_RECOVERY_GUIDE.md)

# Panduan Riset & Pemulihan ZTE ZXV10 B860H V1/V2 (Amlogic S905X)

Dokumen ini berfungsi sebagai panduan teknis lengkap dan referensi untuk memboot Linux Armbian (Kernel 6.x+) pada TV box ZTE B860H V1/V2 dengan **eMMC internal yang mati** — dengan melewati kontroler penyimpanan dan boot langsung dari kartu MicroSD.

---

## 1. Arsitektur Perangkat Keras & Masalah eMMC Mati

### Spesifikasi Perangkat Keras (ZTE B860H V1/V2)

* **SoC**: Amlogic S905X (ARM Cortex-A53 Quad-core)
* **GPU**: ARM Mali-450 MP
* **RAM**: 1GB / 2GB DDR3 (tergantung batch)
* **Antarmuka Penyimpanan**:
  * `mmc0`: Kontroler kartu MicroSD
  * `mmc1`: Kontroler penyimpanan eMMC onboard
* **Chipset Nirkabel**: Realtek RTL8189FS (hanya Wi-Fi, antarmuka SDIO)

### Gejala eMMC Mati

Ketika eMMC internal gagal permanen:

1. Log kernel level rendah menunjukkan `mmc1: Failed to initialize a non-removable card` atau galat I/O berulang.
2. Rantai bootloader Amlogic standar (yang tersimpan pada partisi boot eMMC internal) tidak terbaca, menyebabkan perangkat macet dalam loop boot atau tanpa output serial sama sekali.
3. Papan harus dikonfigurasi agar menjalankan U-Boot sepenuhnya dari kartu SD.

---

## 2. Bypass Bootloader: Suntikan Sektor Mentah

SoC Amlogic memiliki ROM bootloader berkode-keras (BL1) yang memindai media boot untuk mencari tanda bootloader valid (BL2) pada tata sektor tertentu. Untuk kartu MicroSD, ia membaca awal disk.

### Proteksi Partisi MBR

Agar kartu SD bisa-boot sambil partisinya tetap utuh, kita harus menulis biner U-Boot berkemampuan SD-boot (`uboot_HG680P-sdboot.bin`) ke Master Boot Record (Sektor 0) dan sektor-sektor tepat setelahnya. Namun, kita **tidak boleh menimpa tabel partisi MBR** (byte 442 hingga 511 pada sektor 0), jika tidak batas partisi hilang dan partisi FAT serta ext4 rusak.

### Skema Suntikan DD

Suntikan dibagi menjadi dua operasi:

1. **Kode Bootstrap**: Tulis 442 byte pertama U-Boot ke sektor 0 (byte 0–441). Ini berisi instruksi boot awal untuk ROM Amlogic.
2. **Badan U-Boot**: Tulis sisa U-Boot mulai dari byte 512 langsung ke sektor 1 kartu SD.

```text
       Sektor 0 (512 Byte)                            Sektor 1+
+----------------------+----------+---------+   +------------------------------+
| Bootstrap (0-441 B)  | MBR (70B)|Sig (55AA|   |      Badan U-Boot (512 B+)   |
+----------------------+----------+---------+   +------------------------------+
| <-- Tertulis (dd 1)->| Tetap Utuh         |   | <-- Tertulis (dd 2) -------->|
```

Pada python, ini diimplementasikan di [patch_uboot.py](../../tools/patch_uboot.py):

```python
# Tulis kode bootstrap
img.seek(0)
img.write(uboot_data[:442])

# Tulis badan U-Boot (melewati tabel MBR)
img.seek(512)
img.write(uboot_data[512:])
```

---

## 3. Perbaikan Relokasi Kernel: Crash `text_offset`

Kernel Linux mainline ARM64 modern (v5.8+) memakai offset teks kernel bawaan `0` pada header image-nya. Bootloader vendor lawas (seperti U-Boot v2015.01 S905X) menghitung alamat relokasi kernel memakai:

$$\text{relocated\_addr} = \text{ALIGN}(\text{gd->ram\_base}, \text{2MB}) + \text{text\_offset}$$

Karena $\text{gd->ram\_base}$ adalah `0x00000000` dan $\text{text\_offset}$ adalah `0`, U-Boot mencoba menulis kernel langsung ke alamat fisik `0x00000000`.

### Mekanisme Crash

16MB pertama DRAM pada TV box ini adalah memori aman terproteksi yang dicadangkan untuk TrustZone / Secure Monitor (BL30/31/32). Menulis ke `0x0` memicu pengecualian level perangkat keras `Synchronous Abort` (ESR `0x96000210`), menghasilkan crash dan reboot seketika.

### Perbaikan Patch Header

Kami menambal berkas image kernel (`/Image` pada partisi boot FAT32) dengan memodifikasi medan headernya untuk menggeser alamat muat ke wilayah DRAM aman yang dapat ditulis:

* **Offset Byte**: `8` (merepresentasikan medan `text_offset`, integer 64-bit little-endian).
* **Nilai Patch**: `0x1080000` (16,5 MB).
* **String Hex**: `00 00 08 01 00 00 00 00`

Setelah dipatch, U-Boot merelokasi kernel ke `0x01080000`, melewati wilayah memori aman dan memungkinkan kernel boot normal. Ini diimplementasikan di [patch_image_header.py](../../tools/patch_image_header.py).

---

## 4. Penambalan Device Tree Wi-Fi Internal

Blob device tree Linux mainline (seperti `meson-gxl-s905x-p212.dtb`) ditulis untuk papan referensi. Desain generik `p212` memetakan power sequencer Wi-Fi SDIO (`sdio-pwrseq`) pin reset-nya ke Pin GPIO 85.

### Selisih Pemetaan Pin GPIO

* **Papan referensi `p212`**: Pin reset Wi-Fi GPIO = `85` (`0x55`)
* **Tata letak Papan ZTE B860H**: Pin reset Wi-Fi GPIO = `76` (`0x4c`)

Karena kernel menarik Pin 85 ke rendah untuk mereset chip Wi-Fi, modul Wi-Fi fisik pada papan B860H tetap dalam keadaan reset berdaya rendah, gagal merespons pada bus SDIO.

### Perbaikan Patch DTB

Kami menambal DTB terkompilasi (`/dtb/amlogic/meson-gxl-s905x-p212.dtb`) untuk mengubah pemetaan pin dari 85 menjadi 76 secara in-place.

* **Node Properti**: `sdio-pwrseq` -> `reset-gpios`
* **Byte Target**: Format entri GPIO adalah `<phandle pin_index flags>`. Dalam hex:
  * **Asli**: `00 00 00 15 00 00 00 55 00 00 00 01` (Pin 85 / `0x55`)
  * **Dipatch**: `00 00 00 15 00 00 00 4c 00 00 00 01` (Pin 76 / `0x4c`)
* **Offset Berkas**: `28280` (dapat berbeda tergantung build DTB, tetapi dapat ditemukan dinamis dengan mencari sekuens byte).

Ini diimplementasikan di [patch_dtb.py](../../tools/patch_dtb.py).

---

## 5. Temuan & Keterbatasan Diagnostik Bluetooth

Saat boot, kernel melaporkan galat ketika mencoba berbicara dengan kontroler Bluetooth Broadcom:

```text
[   13.669504] Bluetooth: hci0: command 0xfc18 tx timeout
[   13.669504] Bluetooth: hci0: BCM: failed to write update baudrate (-110)
[   13.675650] Bluetooth: hci0: Failed to set baudrate
[   15.684236] Bluetooth: hci0: command 0xfc18 tx timeout
[   15.685323] Bluetooth: hci0: BCM: Reset failed (-110)
```

### Menjelaskan Galat

1. **Deklarasi Device Tree**: DTB generik `p212` mendeklarasikan perangkat Bluetooth Broadcom (`brcm,bcm43438-bt` atau sejenis) yang tersambung ke antarmuka serial `uart_A` (`/dev/ttyS1`).
2. **Perangkat Keras Hilang**: Revisi B860H ini memakai chip **RTL8189FS**. Tidak seperti chip combo (mis. AP6212), RTL8189FS adalah modul **khusus Wi-Fi**. Tidak ada chip Bluetooth Broadcom fisik pada papan.
3. **Timeout (-110)**: Driver kernel mengirim perintah ke port serial mengharapkan respons chip Broadcom. Karena chip tidak ada, transaksi timeout (`-110`), menghasilkan pesan "Reset failed".

### Resolusi

* Tidak ada perubahan konfigurasi yang dapat mengaktifkan Bluetooth onboard karena perangkat kerasnya memang tidak ada secara fisik.
* **Solusi**: Pasang dongle USB Bluetooth standar. Kernel mainline memuat driver untuk chipset USB Bluetooth umum, sehingga plug-and-play.

---

## 6. Runbook Pemulihan Lengkap

Ikuti langkah persis ini bila kartu SD Anda rusak atau Anda perlu membuat yang baru dari nol:

### Langkah 1: Siapkan dan Flash Kartu SD

1. Unduh image Armbian mainline minimal/server untuk `aml-s9xx-box` (mis. Debian Trixie atau Ubuntu Noble).
2. Flash ke kartu MicroSD berkualitas tinggi memakai Rufus atau BalenaEtcher.
3. Dekompresi berkas `.img.xz` terlebih dahulu bila menulis via skrip.

### Langkah 2: Suntikkan Bootloader Kustom

1. Jalankan [patch_uboot.py](../../tools/patch_uboot.py) (atau [`do_dd.sh`](../../tools/do_dd.sh)) dengan target berkas image output atau drive kartu SD mentah. Ini menyuntikkan `firmware/uboot_HG680P-sdboot.bin` sambil menjaga tabel partisi aman.

### Langkah 3: Konfigurasi `uEnv.txt` & Salin Autoscript

Mount partisi `BOOT` pada kartu SD:

1. Salin `aml_autoscript` dari direktori `boot/` repositori ini ke direktori akar partisi `BOOT`.
2. Buat `uEnv.txt` pada akar partisi `BOOT`:

   ```ini
   LINUX=Image
   INITRD=uInitrd
   FDT=dtb/amlogic/meson-gxl-s905x-p212.dtb
   APPEND=root=UUID=<UUID-ROOTFS-ANDA> rootflags=data=writeback console=ttyAML0,115200n8 console=tty0 rw no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0 splash plymouth.ignore-serial-consoles
   ```

   *(Ambil UUID partisi kedua kartu SD yang telah di-flash memakai `blkid` di Linux atau manajer partisi di Windows).*

### Langkah 4: Terapkan Patch pada Berkas Boot

Jalankan skrip pembantu berikut untuk menambal berkas langsung pada partisi kartu SD yang ter-mount:

1. Jalankan [patch_image_header.py](../../tools/patch_image_header.py) untuk mengatur offset teks `BOOT:\Image` menjadi `0x1080000`.
2. Jalankan [patch_dtb.py](../../tools/patch_dtb.py) untuk mengubah pin reset GPIO Wi-Fi pada `BOOT:\dtb\amlogic\meson-gxl-s905x-p212.dtb` menjadi pin `76`.

### Langkah 5: Boot dan Atasi Hang Wi-Fi Boot Pertama

1. Masukkan kartu SD ke TV box lalu nyalakan.
2. Bila pemindaian Wi-Fi macet saat penyiapan awal:
   * Jalankan `sudo armbian-config`.
   * Masuk ke **Network** -> **Advanced Network Configuration** -> **Revert to defaults**.
   * Nyalakan ulang layanan jaringan: `sudo systemctl restart NetworkManager`.

---

## 7. Konsol Serial Perangkat Keras (Pinout UART TTL)

Untuk debugging perangkat keras level rendah dan membaca output BootROM/U-Boot serial secara real-time:

![Pinout UART ZTE B860H](assets/b860h_uart_pinout.png)

### Spesifikasi Header:
- **Label Header pada PCB**: `X2` (terletak tepat di samping lubang sekrup dudukan motherboard).
- **Tata Letak**: header 2×3 (6-pad).

| Lokasi Pin | Label pada Papan | Sambungkan ke USB-TTL | Deskripsi |
| :---: | :---: | :---: | :--- |
| **Baris Atas** | **Gnd** | **GND** | Referensi Ground sinyal |
| **Kiri Bawah** | **Tx** | **RXD** | Transmit dari STB $\to$ Receive pada adapter USB TTL |
| **Kanan Bawah** | **Rx** | **TXD** | Receive ke STB $\to$ Transmit dari adapter USB TTL |

> **Aturan Keselamatan**: Jangan pernah menyambungkan pin VCC (3.3V/5V)! STB bertenaga mandiri via barrel jack DC 12V. Menyambungkan VCC eksternal dapat menyebabkan kerusakan back-feed pada adapter USB TTL atau PC host.

### Pengaturan Terminal Serial:
- **Baud Rate**: `115200`
- **Bit Data**: `8`
- **Paritas**: `None`
- **Bit Stop**: `1`
- **Kontrol Alir**: `None` (8N1)
- **Perintah**: Jalankan `python tools/diagnostics/serial_monitor.py` (otomatis mendeteksi serial CH340).
