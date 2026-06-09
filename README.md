# Tutorial: Cara Bypass Bootloop & Install Armbian di STB ZTE B860H / Fiberhome HG680P

Repositori ini telah disusun menjadi tutorial langkah demi langkah untuk membantu Anda menginstal **Armbian Linux** pada STB **ZTE B860H V1/V2** atau **Fiberhome HG680P** melalui SD card.

Metode di bawah ini secara khusus dirancang untuk mengatasi masalah **"saveenv" bootloop** (stuck logo / recovery terus-menerus) yang sering terjadi apabila eMMC internal STB Anda rusak, terkunci, atau tidak dapat ditulisi. Metode ini langsung mem-bypass penulisan ke eMMC dan membaca bootloader sekunder (`u-boot.ext`) langsung dari kartu SD.

Silakan ikuti langkah-langkah berurutan di bawah ini. File yang dibutuhkan sudah dikelompokkan ke dalam folder bernomor agar mudah diikuti.

---

## 🚀 Langkah 1: Persiapan & Flash Kartu SD
Pertama, kita perlu memasukkan image sistem operasi Armbian ke dalam Kartu MicroSD.
*(Gunakan Kartu MicroSD yang andal, minimal 8GB Class 10).*

1. Buka folder `01-alat-flash`.
2. Jika Anda belum punya aplikasi flasher, Anda bisa menggunakan `BootcardMaker.exe` yang ada di sana, atau unduh [Armbian Imager](https://github.com/armbian/imager) / Balena Etcher.
3. Unduh image Armbian Ophub untuk `Amlogic S9xxx` (contoh: `Armbian_2x.xx_Aml_s9xxx_jammy...img.xz`).
4. Buka aplikasi flasher, pilih image yang sudah diunduh, pilih Kartu SD Anda, lalu klik Flash. Tunggu hingga selesai.

*(Folder `01-alat-flash/file-unlock-usb` berisi file `boot.img` dan `bootloader.img` yang berguna jika Anda sedang melakukan proses unlock USB. Untuk instalasi normal Armbian, lewati saja folder tersebut).*

---

## 🛠️ Langkah 2: Konfigurasi Partisi BOOT
Setelah proses flashing selesai, **cabut dan pasang kembali** kartu SD Anda agar partisi bernama `BOOT` muncul (terbaca) di komputer Anda.

Selanjutnya, Anda perlu meng-copy file wajib dari repositori ini ke dalam partisi `BOOT` tersebut:

### 2A. Menambahkan U-Boot Sesuai Tipe STB
Buka folder `03-file-uboot`. Di dalamnya terdapat dua folder sesuai tipe STB:
- `ZTE-B860H`
- `Fiberhome-HG680P`

Pilih folder yang sesuai dengan STB Anda, lalu:
1. Copy file `uboot.bin` di dalamnya.
2. Paste (tempel) file tersebut ke bagian paling luar (root) dari partisi `BOOT` di kartu SD Anda.
3. Ubah nama (rename) file `uboot.bin` yang baru dipaste tersebut persis menjadi **`u-boot.ext`**. *(Langkah ini mengaktifkan bootloader sekunder).*

### 2B. Konfigurasi Device Tree (DTB) & WiFi
Buka folder `04-file-dtb-wifi`. 
1. Copy file `meson-gxl-s905x-p212.dtb`.
2. Paste ke partisi `BOOT` di dalam folder `/dtb/amlogic/` pada kartu SD Anda (timpa jika sudah ada).
3. Di partisi `BOOT`, buka file `uEnv.txt` (atau `extlinux/extlinux.conf`).
4. Cari baris `FDT` dan ubah nilainya agar mengarah ke dtb p212 tadi:
   ```ini
   FDT=/dtb/amlogic/meson-gxl-s905x-p212.dtb
   ```
5. Simpan file tersebut.

*(Baca file `README.md` di folder `04-file-dtb-wifi` untuk informasi perbaikan WiFi lebih lanjut jika diperlukan nanti).*

### 2C. Menerapkan Bypass Bootloop (Wajib)
Buka folder `02-file-boot-wajib`. File di folder ini wajib digunakan untuk melewati masalah eMMC yang rusak.
1. Copy file `aml_autoscript` dan `s905_autoscript`.
2. Paste kedua file tersebut ke root partisi `BOOT` di kartu SD Anda.
3. (Opsional) Jika di partisi `BOOT` kartu SD sudah ada file `aml_autoscript` bawaan sistem, **timpa (replace)** saja dengan file yang baru Anda copy ini.
4. Anda juga bisa menyalin file `fstab.template` jika ingin mengatur partisi secara manual nanti.

---

## 🔌 Langkah 3: Mem-boot STB
Setelah semua file di-copy dan diatur di kartu SD:

1. Cabut kartu SD dari komputer dengan aman (Eject).
2. Pastikan STB dalam keadaan mati (adaptor tidak dicolok).
3. Masukkan Kartu SD ke slot MicroSD STB.
4. Colokkan kabel power adaptor ke STB.
5. Perangkat akan secara otomatis membaca `aml_autoscript` dari kartu SD, menghindari loop memori internal, dan langsung mem-boot **Armbian Linux**!

---

## 📝 Login Pertama
Jika dihubungkan ke monitor/TV via HDMI, Anda akan melihat proses boot Linux. Setelah selesai:
*   **Username Default:** `root`
*   **Password Default:** `1234`

Anda akan diminta untuk membuat password baru dan membuat user biasa (non-root) segera setelah Anda berhasil login.

---

### 📚 Referensi Lanjut
Bagi pengembang (developer) yang ingin tahu lebih dalam, Anda dapat melihat folder `referensi-lanjut`:
- `kompilasi-skrip/`: Berisi skrip Python (`make_aml_autoscript.py`) dan teks mentah script boot jika Anda ingin memodifikasi atau mengompilasi ulang perintah boot STB menggunakan `mkimage`.
- `log-uart/`: Berisi rekaman log UART (`stb_boot_log.txt`) yang mendokumentasikan bagaimana proses bypass ini bekerja pada level hardware.
