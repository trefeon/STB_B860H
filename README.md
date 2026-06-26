# Panduan Lengkap: Bypass eMMC Mati & Booting Armbian Langsung dari SD Card di ZTE B860H V1/V2

Repositori ini berisi dokumentasi, skrip otomatisasi, dan panduan langkah demi langkah untuk menginstal dan menjalankan **Armbian Linux** (Kernel Mainline 6.x) pada STB **ZTE ZXV10 B860H V1/V2** yang mengalami **kerusakan hardware eMMC internal total (dead eMMC)**.

Ketika eMMC internal rusak total, metode boot standard (mengandalkan bootloader internal eMMC untuk memanggil `u-boot.ext`) tidak akan berfungsi. Panduan ini menjelaskan cara mem-bypass eMMC sepenuhnya dengan menulis bootloader langsung ke sektor raw SD card, melakukan patching header kernel agar tidak crash, serta melakukan patching DTB agar Wi-Fi internal dapat berfungsi.

---

## 🛠️ Ringkasan Proses Instalasi

Proses bypass dan boot terdiri dari 5 tahapan utama:

```text
[1. Flash Image] ➔ [2. Inject U-Boot ke Raw SD] ➔ [3. Patch Kernel Header (Bypass Crash)] ➔ [4. Patch DTB (Aktifkan Wi-Fi)] ➔ [5. Colok & Boot]
```

---

## 🚀 Langkah 1: Flash Armbian ke Kartu SD

1. Siapkan kartu MicroSD (minimal 8GB, Class 10 atau lebih cepat).
2. Download image Armbian terbaru untuk **Amlogic S9xxx Box** (contoh: `Armbian_community_26.8.0_Aml-s9xx-box_trixie_current_6.18.35_minimal.img.xz`).
3. Flash image tersebut ke kartu SD menggunakan Rufus, BalenaEtcher, atau Win32DiskImager.

---

## 💾 Langkah 2: Inject U-Boot ke Sektor Raw Kartu SD (Penting)

Karena eMMC mati, SoC Amlogic harus membaca bootloader langsung dari sektor raw kartu SD. Kita harus menyuntikkan U-Boot dengan tetap mempertahankan tabel partisi MBR agar kartu SD tidak rusak/tidak terbaca.

Kami menyediakan skrip otomatis untuk melakukan hal ini:

* **Pengguna Windows:** Jalankan skrip Python:

  ```bash
  python patch_uboot.py
  ```

  *(Skrip ini akan mengambil file `uboot_HG680P.bin` di folder Bahan dan menulis bagian bootstrap ke bytes 0-441 serta body U-Boot mulai byte 512 ke kartu SD Anda).*

* **Pengguna Linux / Git Bash:** Jalankan shell script:

  ```bash
  ./do_dd.sh
  ```

---

## 📝 Langkah 3: Konfigurasi File Boot & Patching Header Kernel (Bypass Crash)

Setelah menulis U-Boot ke sektor raw, cabut dan pasang kembali kartu SD di komputer Anda agar partisi `BOOT` muncul kembali.

### 3A. Menyalin File Boot Wajib

1. Salin file `aml_autoscript` dari folder `[Tertechan] ZTE B860H V1-V2 no eMMC/Bahan/Copy ke BOOT/` ke root partisi `BOOT` kartu SD Anda.
2. Buat file bernama **`uEnv.txt`** di root partisi `BOOT` kartu SD dengan konfigurasi berikut:

   ```ini
   LINUX=Image
   INITRD=uInitrd
   FDT=dtb/amlogic/meson-gxl-s905x-p212.dtb
   APPEND=root=UUID=ganti-dengan-uuid-rootfs-anda rootflags=data=writeback console=ttyAML0,115200n8 console=tty0 rw no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0 splash plymouth.ignore-serial-consoles
   ```

### 3B. Patching Header Kernel (`f:\Image`) untuk Bypass Crash

* **Masalah:** Kernel mainline modern (v5.8+) menggunakan `text_offset` bernilai `0`. U-Boot versi vendor menghitung alamat tujuan relokasi menggunakan rumus `ALIGN(start_ram, 2MB) + text_offset = 0 + 0 = 0x0`. Menulis kernel ke `0x0` akan memicu hardware exception `Synchronous Abort` (ESR `0x96000210`) karena area tersebut adalah memori terproteksi (Secure Monitor / TrustZone).
* **Solusi:** Jalankan skrip Python pembantu untuk mem-patch nilai `text_offset` di dalam file `Image` menjadi `0x1080000` (16.5 MB):

  ```bash
  python patch_image_header.py
  ```

  *(Skrip akan otomatis membuat backup `Image.bak` dan menulis bytes `00 00 08 01 00 00 00 00` ke offset byte 8 dari file `Image` di kartu SD Anda).*

---

## 📶 Langkah 4: Patching Device Tree (DTB) untuk Wi-Fi B860H

DTB bawaan generic (`meson-gxl-s905x-p212.dtb`) memetakan pin reset Wi-Fi SDIO pada pin 85. Namun, layout fisik board ZTE B860H memetakan pin reset tersebut pada GPIO pin **76**.

Untuk memperbaikinya tanpa merusak kompatibilitas kernel mainline:

1. Jalankan skrip Python:

   ```bash
   python patch_dtb.py
   ```

   *(Skrip ini akan mem-patch file `dtb/amlogic/meson-gxl-s905x-p212.dtb` di kartu SD secara in-place pada offset file `28280`, mengubah nilai reset pin dari `85` (`0x55`) menjadi `76` (`0x4c`)).*

2. Kernel modern sekarang dapat melakukan power-on pada chip Wi-Fi secara otomatis dan memuat driver yang tepat (`brcmfmac` / `rtl8723bs`).

---

## 🔌 Langkah 5: Hubungkan & Booting

1. Lepaskan kartu SD secara aman (Eject) dari PC Anda.
2. Pastikan STB dalam keadaan mati, lalu masukkan kartu SD ke slot MicroSD STB.
3. Hubungkan kabel Serial TTL ke PC Anda dan colokkan kabel power STB.
4. Perangkat akan secara otomatis membaca `aml_autoscript` dari kartu SD, menghindari loop memori internal, dan langsung mem-boot **Armbian Linux**!
5. Setelah proses boot selesai, Anda akan diminta mengisi password root baru pada serial monitor:

   ```text
   IP address: Waiting for local connection!
   Create root password:
   ```

6. Nikmati STB B860H Anda yang kini berfungsi penuh menjalankan OS Linux langsung dari kartu SD!

---

## 💡 Tips & Solusi Masalah Wi-Fi

Jika pemindaian (scanning) Wi-Fi macet (hang) atau tidak memunculkan daftar koneksi saat pertama kali setup:

1. Buka konfigurasi Armbian dengan menjalankan:

   ```bash
   sudo armbian-config
   ```

2. Masuk ke **Network** -> **Advanced Network Configuration**.
3. Pilih opsi untuk mengembalikan pengaturan jaringan ke **Armbian defaults** (revert to Armbian default).
4. Restart layanan jaringan atau restart STB Anda. Proses scanning dan koneksi Wi-Fi akan berjalan lancar!
