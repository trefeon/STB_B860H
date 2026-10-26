> Terjemahan Bahasa Indonesia dari ../README.md (English canonical).
> Kembali ke dokumen Inggris: [README.md](../../README.md)

# Toolkit Armbian & Panduan Instalasi untuk ZTE ZXV10 B860H V1/V2 (Amlogic S905X)

Repositori ini berisi panduan teknis, investigasi, skrip otomasi, dan alat diagnostik untuk menjalankan **Linux Armbian** pada STB **ZTE ZXV10 B860H**, mencakup dua skenario utama:

1. **eMMC Sehat / Baru**: Panduan instalasi Armbian modern (**Debian 12 Bookworm / Linux Kernel 6.12.y LTS**), pembersihan firmware exploit pasar (PPPwn), migrasi penuh ke eMMC internal, penyiapan Swap Virtual Memory, dan pemakaian ulang kartu MicroSD sebagai penyimpanan internal permanen (30 GB).
   👉 **[Baca Panduan Lengkap Armbian 6.x Modern (eMMC & MicroSD)](../MODERN_ARMBIAN_6X_INSTALL_GUIDE.md)**

2. **Perangkat dengan eMMC Mati (Perangkat Keras eMMC Mati/Rusak)**: Panduan melewati bootloader eMMC internal dengan menyuntikkan U-Boot langsung ke sektor mentah (raw sector) kartu MicroSD, penambalan (patching) relokasi kernel, dan penambalan DTB.
   👉 **[Baca Panduan Pemulihan eMMC Mati (Bypass Lawas)](../PERMANENT_SD_BOOT_GUIDE.md)**

---

## 🚀 Mulai Cepat: Armbian 6.12 LTS Modern pada eMMC & Penyimpanan SD

Bagi pemilik STB B860H dengan eMMC sehat (termasuk bekas unit PPPwn / Android TV):

1. **Unduh Image Resmi**:
   ```bash
   bash tools/download_image.sh
   ```
   *(Mengunduh `Armbian_26.11.0_amlogic_s905x-b860h_bookworm_6.12.112_server` dan mengekstraknya menjadi `Armbian_b860h.img` di direktori kerja Anda)*.

2. **Flash ke MicroSD**:
   Jalankan `python tools/flash_sd.py` (Jalankan sebagai Administrator) atau gunakan BalenaEtcher/Rufus.

3. **Konfigurasi `uEnv.txt` pada Partisi `BOOT` (Penting)**:
   Pastikan baris `APPEND` memuat `rootdelay=10` dan `root=LABEL=ROOTFS`:
   ```ini
   FDT=/dtb/amlogic/meson-gxl-s905x-b860h.dtb
   APPEND=root=LABEL=ROOTFS rootdelay=10 rootflags=data=writeback rw rootwait rootfstype=ext4 console=ttyAML0,115200n8 console=tty0 no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0 max_loop=128 cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory swapaccount=1 video=HDMI-A-1:1920x1080@60e plymouth.enable=0
   ```

4. **Boot MicroSD & Migrasi ke eMMC**:
   - Masukkan MicroSD ke STB lalu nyalakan. Masuk via SSH (`root` / kata sandi bawaan image).
   - Jalankan `sudo armbian-install` $\to$ masukkan ID `106` (B860H) $\to$ pilih `1` (ext4).

5. **Siapkan Swap & Gunakan Ulang MicroSD sebagai Penyimpanan**:
   - Matikan STB (`poweroff`), lepaskan MicroSD, lalu nyalakan kembali STB (STB melakukan boot dari eMMC internal).
   - Masukkan kembali MicroSD, lalu jalankan:
     ```bash
     sudo /root/setup_sd_storage.sh
     ```
   - MicroSD otomatis diformat ulang menjadi `ext4` murni (label `SD_STORAGE`) dan di-mount pada `/mnt/storage` dan `/home/<user>/storage`.

6. **Cek Kesehatan Sistem via SSH & Bash Bawaan**:
   ```bash
   # Jalankan skrip diagnostik (otomatis via SSH tanpa kata sandi)
   bash tools/diagnostics/ssh_check.sh

   # Atau sambungkan langsung dari pintasan Windows:
   ssh stb       # Akses via LAN kabel (<STB-LAN-IP>; mis. 192.168.1.100)
   ssh stb-wifi  # Akses via cadangan Wi-Fi (<STB-WIFI-IP>)
   ssh stb-ts    # Akses via VPN Tailscale (<TAILSCALE-IP>)
   ```

7. **Paket Auto-Patch Turnkey Offline Wi-Fi & DTB**:
   Untuk STB baru, jalankan satu perintah dari PC/laptop tanpa perlu kompilasi di perangkat:
   ```bash
   bash tools/ship_patch.sh stb
   ```
   *(Otomatis memasang driver Wi-Fi `8189fs.ko` dan DTB `meson-gxl-s905x-b860h.dtb` dalam < 2 detik tanpa internet)*.

8. **Pinout UART Perangkat Keras & Pemulihan Cold Boot**:
   Jika menemui masalah bootloader / hang saat cold boot, sambungkan adapter USB TTL ke header `X2` pada PCB B860H:
   - **Gnd** $\to$ `GND`
   - **Tx** $\to$ `RXD`
   - **Rx** $\to$ `TXD`
   - Jalankan `python tools/diagnostics/boot_monitor.py` (Baudrate: `115200`) — mendeteksi setiap reboot, memberi stempel waktu, dan melaporkan vonis hang otomatis. `serial_monitor.py` tersedia sebagai cadangan raw-tee.
   - Panduan lengkap: 👉 **[Baca Bab 11 Troubleshooting eMMC & Cold Boot](../MODERN_ARMBIAN_6X_INSTALL_GUIDE.md#11-troubleshooting--playbook-emmc-cold-boot--microsd-storage)**
---

## 🛠️ Panduan Bypass eMMC Mati (Bypass Perangkat Keras Lawas)

*(Bagian berikut ditujukan untuk unit B860H yang perangkat keras eMMC internalnya mati total).*

---

### Ringkasan Proses Bypass

Repositori ini berisi dokumentasi, skrip otomasi, dan panduan langkah demi langkah untuk memasang dan menjalankan **Linux Armbian** (Mainline Kernel 6.x) pada STB **ZTE ZXV10 B860H V1/V2** yang mengalami **kegagalan total perangkat keras eMMC internal (eMMC mati)**.

Ketika eMMC internal mati total, metode boot standar (yang mengandalkan bootloader eMMC internal untuk memanggil `u-boot.ext`) tidak akan berfungsi. Panduan ini menjelaskan cara melewati eMMC sepenuhnya dengan menulis bootloader langsung ke sektor mentah kartu SD, menambal header kernel agar tidak crash, dan menambal DTB agar Wi-Fi internal berfungsi.

---

## 🛠️ Ringkasan Proses Instalasi

Prosedur bypass dan boot terdiri dari 5 tahap utama:

```text
[1. Flash Image] ➔ [2. Suntik U-Boot ke Raw SD] ➔ [3. Patch Header Kernel (Cegah Crash)] ➔ [4. Patch DTB (Aktifkan Wi-Fi)] ➔ [5. Colok & Boot]
```

---

## 🚀 Langkah 1: Flash Armbian ke Kartu SD

1. Siapkan kartu MicroSD (minimal 8GB, Class 10 atau lebih cepat).
2. Unduh image Armbian terbaru untuk **Amlogic S9xxx Box** (contoh: `Armbian_community_26.8.0_Aml-s9xx-box_trixie_current_6.18.35_minimal.img.xz`).
3. Flash image tersebut ke kartu SD menggunakan Rufus, BalenaEtcher, atau Win32DiskImager.

---

## 💾 Langkah 2: Suntikkan U-Boot ke Sektor Mentah Kartu SD (Penting)

Karena eMMC mati, SoC Amlogic harus membaca bootloader langsung dari sektor mentah kartu SD. Kita harus menyuntikkan U-Boot sambil menjaga tabel partisi MBR agar kartu SD tetap utuh/terbaca.

Kami menyediakan skrip otomatis untuk itu:

* **Pengguna Windows:** Jalankan skrip Python:

  ```bash
  python tools/patch_uboot.py
  ```

  *(Skrip ini mengambil berkas `uboot_HG680P-sdboot.bin` di folder `firmware/` lalu menulis bagian bootstrap ke byte 0-441 plus badan U-Boot mulai dari byte 512 ke kartu SD Anda).*

* **Pengguna Linux / Git Bash:** Jalankan skrip shell:

  ```bash
  ./tools/do_dd.sh
  ```

---

## 📝 Langkah 3: Konfigurasi Berkas Boot & Penambalan Header Kernel (Cegah Crash)

Setelah menyuntikkan U-Boot ke sektor mentah, lepaskan lalu colokkan kembali kartu SD pada komputer agar partisi `BOOT` muncul kembali.

### 3A. Menyalin Berkas Boot yang Dibutuhkan

1. Salin berkas `aml_autoscript` dari folder `boot/` ke akar partisi `BOOT` pada kartu SD.
2. Buat berkas bernama **`uEnv.txt`** pada akar partisi `BOOT` kartu SD dengan konfigurasi berikut:

   ```ini
   LINUX=Image
   INITRD=uInitrd
   FDT=dtb/amlogic/meson-gxl-s905x-p212.dtb
   APPEND=root=UUID=ganti-dengan-uuid-rootfs-anda rootflags=data=writeback console=ttyAML0,115200n8 console=tty0 rw no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0 splash plymouth.ignore-serial-consoles
   ```

### 3B. Menambal Header Kernel (`Image`) untuk Cegah Crash

* **Masalah:** Kernel mainline modern (v5.8+) memakai nilai `text_offset` sebesar `0`. U-Boot vendor menghitung alamat tujuan relokasi dengan rumus `ALIGN(start_ram, 2MB) + text_offset = 0 + 0 = 0x0`. Menulis kernel ke `0x0` memicu pengecualian perangkat keras `Synchronous Abort` (ESR `0x96000210`) karena wilayah tersebut adalah memori terproteksi (Secure Monitor / TrustZone).
* **Solusi:** Jalankan skrip Python pembantu untuk menambal nilai `text_offset` di dalam berkas `Image` menjadi `0x1080000` (16,5 MB):

  ```bash
  python tools/patch_image_header.py
  ```

  *(Skrip otomatis membuat cadangan `Image.bak` dan menulis byte `00 00 08 01 00 00 00 00` pada offset byte 8 di berkas `Image` pada kartu SD Anda. Anda juga bisa memberikan path/drive kustom sebagai argumen, misalnya: `python tools/patch_image_header.py g:\Image`).*

---

## 📶 Langkah 4: Menambal Device Tree (DTB) untuk Wi-Fi B860H

DTB generik bawaan (`meson-gxl-s905x-p212.dtb`) memetakan pin reset Wi-Fi SDIO ke pin 85. Namun, tata letak papan ZTE B860H memetakan pin reset tersebut ke pin GPIO **76**.

Untuk memperbaikinya tanpa merusak kompatibilitas kernel mainline:

1. Jalankan skrip Python:

   ```bash
   python tools/patch_dtb.py
   ```

   *(Skrip ini menambal berkas `dtb/amlogic/meson-gxl-s905x-p212.dtb` pada kartu SD secara in-place pada offset berkas `28280`, mengubah nilai pin reset dari `85` (`0x55`) menjadi `76` (`0x4c`). Anda juga bisa memberikan path berkas DTB kustom sebagai argumen, misalnya: `python tools/patch_dtb.py g:\dtb\amlogic\meson-gxl-s905x-p212.dtb`).*

2. Kernel modern kini dapat menyalakan chip Wi-Fi secara otomatis dan memuat driver yang tepat (`brcmfmac` / `rtl8723bs`).

---

## 🔌 Langkah 5: Sambungkan & Boot

1. Lepaskan kartu SD secara aman (Eject) dari PC.
2. Pastikan STB dalam keadaan mati, lalu masukkan kartu SD ke slot MicroSD STB.
3. Sambungkan kabel Serial TTL ke PC lalu colokkan kabel daya STB.
4. Perangkat otomatis membaca `aml_autoscript` dari kartu SD, menghindari loop memori internal, dan melakukan boot **Linux Armbian** langsung!
5. Setelah proses boot selesai, Anda akan diminta memasukkan kata sandi root baru pada monitor serial:

   ```text
   IP address: Waiting for local connection!
   Create root password:
   ```

6. Nikmati STB B860H Anda yang kini berjalan penuh dengan OS Linux langsung dari kartu SD!

---

## 💡 Tips Wi-Fi & Troubleshooting

Jika pemindaian Wi-Fi macet atau tidak menampilkan daftar koneksi pada penyiapan pertama:

1. Buka konfigurasi Armbian dengan menjalankan:

   ```bash
   sudo armbian-config
   ```

2. Masuk ke **Network** -> **Advanced Network Configuration**.
3. Pilih opsi untuk mengembalikan pengaturan jaringan ke **bawaan Armbian**.
4. Nyalakan ulang layanan jaringan atau reboot STB Anda. Pemindaian dan koneksi Wi-Fi kemudian akan berjalan lancar!

---

## 📂 Struktur Repositori

Repositori ini disusun dengan struktur bersih sebagai berikut:

* **[`boot/`](../../boot/)**: Skrip boot aktif saja (`aml_autoscript` + sumber, `emmc_autoscript` + sumber).
* **[`firmware/`](../../firmware/)**: Biner bootloader (`uboot_B860H-emmc-stock.bin`, `uboot_HG680P-sdboot.bin`), DTB referensi stok (`meson-gxl-s905x-p212-stock-unpatched.dtb`), dan set unbrick lawas (`legacy/`).
* **[`tools/`](../../tools/)**: Berisi skrip otomasi (konvensi: **bash+ssh** untuk perintah STB, **Python** hanya untuk pekerjaan serial-UART/parsing-biner/raw-disk Windows):
  * `download_image.sh`: Unduh + ekstrak image Ophub (`curl` + `gunzip`).
  * `flash_sd.py`, `flash_android_p2.py`, `partition_usb_android.py`, `simg2img.py`: I/O raw-disk / format-biner Windows (tidak ada padanan bash).
  * `tools/vendor/`: Blob vendor pihak ketiga tanpa sumber (`ampack.exe`, pack/unpack image Amlogic).
  * `patch_uboot.py` / `do_dd.sh`: Suntikan U-Boot ke sektor mentah (Python dengan deteksi image otomatis, atau `dd` pada bash/Linux) — pilih salah satu.
  * `patch_dtb.py`, `patch_image_header.py`, `mkimage_script.py`, `find_gpio_offset.py`, `diff_dtb.py`, `read_dtb.py`, `read_header.py`: Utilitas biner/DTB (Python, semua path via argumen).
  * `diagnostics/boot_monitor.py`: Monitor UART utama — mendeteksi setiap reboot, memberi stempel waktu, vonis hang otomatis.
  * `diagnostics/test_bootm.py [--image F --bootargs "..."]`: Uji boot `bootm` dari USB (pengganti test_boot_stock/boot_android_test).
  * `diagnostics/auto_restore_linux.py`, `serial_recovery.py`, `test_chainload_uboot.py`, `uboot_interactive.py`: Interaksi prompt U-Boot via port serial (mis. `<COM-PORT>` di Windows; contoh `COM5`).
  * `diagnostics/*.sh`, `optimizations/*.sh`, `ship_patch.sh`, `auto_patch_wifi_bt.sh`: Audit SSH, patching, dan tuning (bash).
  * `hdmi-console.sh` + `99-hdmi-console.rules`: Kebijakan konsol HDMI pada STB (blank + matikan getty saat HDMI dicabut).
  * `hotspot-failover.sh` + `.service`/`.timer`: AP Darurat — menyalakan `B860H-AP` setelah 2x pemeriksaan uplink gagal, mematikannya saat uplink pulih (SSH di `192.168.50.1`, default AP perangkat sebagai contoh).
* **[`packages/`](../../packages/)**: Bundel siap-pasang — `b860h_patch/` (perbaikan Wi-Fi/DTB Armbian), `android_custom/` (APK sideload), `stock-roms/` (stok Android FWAero/Pulpstone, hanya di disk, diabaikan git).
* **[`docs/`](../)**: Panduan instalasi eMMC & MicroSD modern, riset perangkat keras, dan panduan pemulihan SD — mulai dari [`STB_B860H_FULL_SETUP_GUIDE.md`](../STB_B860H_FULL_SETUP_GUIDE.md) untuk penyiapan persis box ini dari ujung ke ujung.
---

## 🔧 Boot Deterministik (Perbaikan untuk Prompt `gxl_p212_v1#`)

U-Boot vendor (`bootcmd=run storeboot`) tidak memiliki hook untuk skrip eMMC — kadang boot, kadang berhenti di prompt. Perbaikan permanen (sudah diterapkan pada STB ini):

1. `/boot/emmc_autoscript` + `/boot/aml_autoscript` = skrip deterministik (perangkat eksplisit `mmc 1:1`, tanpa probing USB/SD, tanpa `saveenv`), dikompilasi **di STB** via `mkimage`.
2. `setenv bootcmd 'fatload mmc 1:1 0x01020000 emmc_autoscript; autoscr 0x01020000'; saveenv` — boot selalu melewati skrip eMMC.

Catatan: jangan pernah mengirim perintah yang mengandung `${...}` melalui alat SSH berbasis string (variabel bisa hilang sebelum sampai). Gunakan literal, atau ketik perintah U-Boot via sesi interaktif/serial Python.

## 🖥 Kebijakan Konsol HDMI

`tools/hdmi-console.sh` + aturan udev (terpasang di `/usr/local/bin`, `/etc/udev/rules.d/99-hdmi-console.rules`): HDMI tersambung → unblank + `getty@tty1` menyala; HDMI dicabut → output diblankan + getty mati untuk beban ringan (server murni).
