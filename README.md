# Panduan Boot SD Card Armbian ZTE B860H (Solusi Bootloop)

Repositori ini menyediakan metode yang andal untuk mem-boot **Armbian Linux** pada **ZTE B860H V1/V2 (Amlogic S905X - Board p212)** melalui SD card (kartu SD). 

Panduan spesifik ini dirancang untuk mem-bypass (melewati) masalah umum **bootloop "saveenv"** yang terjadi ketika eMMC internal STB (Set-Top Box) mengalami kerusakan, terkunci, atau tidak dapat ditulisi.

## 🌟 Mengapa menggunakan metode ini?

File `aml_autoscript` standar dari Armbian mencoba menulis variabel boot ke penyimpanan internal perangkat (`saveenv`). Jika eMMC Anda rusak, proses ini akan gagal, dan STB akan mengalami bootloop (mengulang terus-menerus) masuk ke mode recovery atau hanya mentok di logo boot.

Dengan menggunakan skrip yang disediakan di repositori ini, kita menginstruksikan STB untuk **langsung melakukan chainload** bootloader sekunder (`u-boot.ext`) dari kartu SD, sepenuhnya melewati segala proses penulisan ke memori internal.

---

## 🚀 Panduan Instalasi

### 1. Flash Kartu SD
1. Siapkan Kartu MicroSD yang andal (minimal 8GB, Class 10).
2. Unduh [Armbian Imager](https://github.com/armbian/imager) (Sangat Disarankan) atau gunakan Balena Etcher.
3. Pilih image Armbian Ophub untuk `Amlogic S9xxx` (berformat `.img.xz` atau `.img.gz`).
4. Flash image tersebut ke kartu SD Anda dan tunggu hingga selesai.

### 2. Konfigurasi Partisi BOOT
Setelah proses flashing selesai, cabut dan pasang kembali kartu SD Anda agar partisi `BOOT` terbaca di PC. Anda perlu melakukan tiga perubahan penting:

#### A. Aktifkan Bootloader Sekunder
Bootloader bawaan B860H memerlukan ekstensi.
1. Buka partisi `BOOT`.
2. Cari file bernama `u-boot-s905x-s912`.
3. **Ubah nama (Rename)** file tersebut persis menjadi `u-boot.ext`.

#### B. Atur Device Tree (DTB)
Beritahu Armbian perangkat keras apa yang sedang digunakannya:
1. Buka file `uEnv.txt` (atau `extlinux/extlinux.conf` tergantung pada image yang digunakan).
2. Cari baris `FDT`.
3. Ubah nilainya agar mengarah ke device tree p212:
   ```ini
   FDT=/dtb/amlogic/meson-gxl-s905x-p212.dtb
   ```
4. Simpan file tersebut.

#### C. Terapkan Bypass Bootloop (Langkah Krusial)
Jika Anda mengalami masalah eMMC, lakukan ini untuk mencegah bootloop:
1. Di partisi `BOOT`, cari file `s905_autoscript`.
2. Hapus (atau ubah nama) file `aml_autoscript` yang sudah ada.
3. **Salin (Copy)** `s905_autoscript` dan **Ubah Nama (Rename)** hasil salinannya menjadi `aml_autoscript`.

*(Sebagai alternatif, Anda dapat mengunduh `aml_autoscript` yang sudah dikompilasi dari folder `boot-scripts/` di repositori ini dan menimpanya ke kartu SD Anda).*

### 3. Mem-boot STB
1. Pastikan STB dalam keadaan mati (tidak tersambung listrik).
2. Masukkan Kartu SD yang telah disiapkan.
3. Colokkan kabel daya (power).
4. Perangkat akan secara otomatis membaca `aml_autoscript` dari kartu SD dan langsung mem-boot Armbian Linux!

---

## 🛠️ Isi Repositori

*   `boot-scripts/`: Berisi skrip bypass boot yang sudah dikompilasi (`aml_autoscript` dan `s905_autoscript`).
*   `src/`: Berisi teks skrip Ophub asli yang dapat dibaca manusia dan kompilator python (`make_aml_autoscript.py`) jika Anda ingin membuat skrip sendiri menggunakan `mkimage`.
*   `logs/`: Berisi referensi log boot UART yang mendemonstrasikan keberhasilan bypass dari kegagalan `saveenv`.

---

## 📝 Login Pertama
Setelah sistem berhasil boot dan terhubung ke jaringan Anda:
*   **Username:** `root`
*   **Password Default:** `1234`

Anda akan diminta untuk segera mengubah password pada saat pertama kali login.
