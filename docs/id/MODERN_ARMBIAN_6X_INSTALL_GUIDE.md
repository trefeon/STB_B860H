> Terjemahan Bahasa Indonesia dari ../MODERN_ARMBIAN_6X_INSTALL_GUIDE.md (English canonical).
> Kembali ke dokumen Inggris: [MODERN_ARMBIAN_6X_INSTALL_GUIDE.md](../MODERN_ARMBIAN_6X_INSTALL_GUIDE.md)

# Panduan Lengkap: Instalasi Armbian Modern (Kernel 6.x LTS), Pembersihan PPPwn, Migrasi eMMC, dan MicroSD sebagai Penyimpanan pada ZTE B860H

Panduan ini mendokumentasikan investigasi teknis, pembersihan firmware pihak ketiga (PPPwn PS4 HEN), instalasi **Armbian modern (Debian 12 Bookworm / Linux Kernel 6.12.y LTS)**, migrasi sistem ke eMMC internal, penyiapan Memori Swap, dan pemakaian kartu MicroSD sebagai media penyimpanan internal permanen pada STB **ZTE ZXV10 B860H V1/V2 (Amlogic S905X)**.

---

## 📋 Daftar Isi
1. [Mengidentifikasi & Membersihkan Sisa Firmware Pasar (PPPwn)](#1-mengidentifikasi--membersihkan-sisa-firmware-pasar-pppwn)
2. [Pemilihan Image & Persiapan MicroSD Modern (Kernel 6.12 LTS)](#2-pemilihan-image--persiapan-microsd-modern-kernel-612-lts)
3. [Troubleshooting Boot MicroSD: Memperbaiki ALERT UUID Initramfs](#3-troubleshooting-boot-microsd-memperbaiki-alert-uuid-initramfs)
4. [Memigrasi Sistem ke eMMC Internal (`armbian-install`)](#4-memigrasi-sistem-ke-emmc-internal-armbian-install)
5. [Konfigurasi Memori Virtual Swap (Pendamping RAM 2GB)](#5-konfigurasi-memori-virtual-swap-pendamping-ram-2gb)
6. [Mengonfigurasi MicroSD sebagai Penyimpanan Internal Permanen](#6-mengonfigurasi-microsd-sebagai-penyimpanan-internal-permanen)
7. [Skrip Otomasi & Diagnostik Repositori](#7-skrip-otomasi--diagnostik-repositori)

---

## 1. Mengidentifikasi & Membersihkan Sisa Firmware Pasar (PPPwn)

Banyak box B860H bekas di pasaran dijual sebagai dongle *PlayStation 4 Jailbreak* otomatis (PPPwn) berbasis Armbian 21.08 (Ubuntu 20.04 Focal) yang dimodifikasi skrip seperti `STB-Pwn` (fork dari `PI-Pwn` karya Stooged).

### Temuan Analisis:
- **Celah Akses / UI Web**: Port 80 menjalankan Nginx + PHP-FPM tanpa autentikasi, mengeksekusi perintah shell sebagai `www-data`.
- **Hak Sudoers**: Penjual menambahkan entri `www-data ALL=(ALL) NOPASSWD: ALL` pada `/etc/sudoers`.
- **Spam Log & Partisi Boot Penuh**:
  - Partisi log `zram1` (50MB) 100% penuh oleh auth.log dan monitoring.
  - Partisi `/boot` FAT32 (122MB) 100% penuh oleh rekaman pemulihan `FSCK*.REC` dan berkas APK acak.
- **Loop Proses Exploit**: `pppwn64` berjalan non-stop pada antarmuka `eth0`, membebani CPU dan menimbulkan panas.

### Prosedur Pembersihan:
```bash
# 1. Hentikan layanan dan matikan proses exploit
systemctl stop pipwn pppoe dtlink nginx php7.4-fpm dnsmasq
killall -9 pppwn64 pppwn7 pppwn11 timeout
systemctl disable pipwn pppoe dtlink nginx php7.4-fpm dnsmasq
rm -f /etc/systemd/system/pipwn.service /etc/systemd/system/pppoe.service /etc/systemd/system/dtlink.service
systemctl daemon-reload

# 2. Bersihkan sisa PPPwn dan rc.local
rm -rf /boot/firmware/PPPwn /media/pwndrives /etc/udev/rules.d/99-pwnmnt.rules
sed -i '/PPPwn/d' /etc/rc.local
sed -i '/devboot.sh/d' /etc/rc.local

# 3. Pulihkan sudoers dan flush iptables
sed -i '/www-data.*ALL/d' /etc/sudoers
iptables -P INPUT ACCEPT && iptables -P FORWARD ACCEPT && iptables -P OUTPUT ACCEPT
iptables -t nat -F && iptables -t mangle -F && iptables -F && iptables -X

# 4. Bersihkan berkas sampah dari partisi /boot
rm -f /boot/*.apk /boot/*.dpkg-bak /boot/FSCK*.REC
rm -rf /boot/LOST.DIR /boot/Android /boot/firmware
```

---

## 2. Pemilihan Image & Persiapan MicroSD Modern (Kernel 6.12 LTS)

Untuk menjalankan Linux modern, gunakan build teruji dari proyek **Ophub Amlogic**:
- **Image Resmi**: `Armbian_26.11.0_amlogic_s905x-b860h_bookworm_6.12.112_server_2026.10.15.img.gz` (Debian 12 Bookworm, Kernel 6.12.112 LTS).
- **Alat Unduh**: `tools/download_and_prep_image.py` (otomatis mengunduh dan mendekompresi ke `Armbian_b860h.img`).
- **Alat Flashing Windows**: `tools/flash_sd.py` (menulis langsung ke blok mentah `\\.\PhysicalDriveX` memakai API kernel32 Win32).

---

## 3. Troubleshooting Boot MicroSD: Memperbaiki ALERT UUID Initramfs

### Gejala:
Saat kartu MicroSD pertama kali diboot pada TV box, proses boot U-Boot dan kernel berhasil, tetapi proses macet pada prompt BusyBox dengan galat:
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

### Penyebab:
Driver MMC (`meson-gx-mmc`) butuh 3-5 detik untuk mendeteksi slot kartu MicroSD, tetapi initramfs bawaan Ubuntu/Debian memeriksa UUID seketika dan langsung menyerah (*timeout*).

### Perbaikan Permanen pada `uEnv.txt`:
Colokkan kembali kartu MicroSD ke PC, buka partisi `BOOT` (FAT32), lalu edit baris `APPEND` pada berkas `uEnv.txt`:
```text
LINUX=/zImage
INITRD=/uInitrd
FDT=/dtb/amlogic/meson-gxl-s905x-b860h.dtb
APPEND=root=LABEL=ROOTFS rootdelay=10 rootflags=data=writeback rw rootwait rootfstype=ext4 console=ttyAML0,115200n8 console=tty0 no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0 max_loop=128 cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory swapaccount=1 video=HDMI-A-1:1920x1080@60e plymouth.enable=0
```
- **`root=LABEL=ROOTFS`**: Mencari label partisi ext4 secara langsung tanpa mengandalkan resolusi UUID udev yang tertunda.
- **`rootdelay=10`**: Memberi jeda penuh 10 detik agar kontroler kartu SD selesai diinisialisasi.

---

## 4. Memigrasi Sistem ke eMMC Internal (`armbian-install`)

Setelah boot dari MicroSD berhasil dan terjangkau via SSH:

1. Jalankan skrip instalasi eMMC:
   ```bash
   sudo armbian-install
   ```
2. Masukkan parameter berikut saat diminta:
   - **ID Box**: Masukkan `106` (model ZTE B860H, SoC `s905x`, DTB `meson-gxl-s905x-b860h.dtb`).
   - **Root Filesystem**: Masukkan `1` (`ext4`).
3. Skrip otomatis:
   - Mencadangkan bootloader eMMC asli ke `/usr/lib/u-boot/mybox-bootloader.img`.
   - Mempartisi ulang eMMC internal menjadi partisi boot **512 MB** yang lapang (`BOOT_EMMC`) dan sisanya **6,1 GB** untuk root (`ROOTFS_EMMC`).
   - Menyalin bootloader dan kernel, serta merysync seluruh berkas rootfs ke eMMC.

---

## 5. Arsitektur eMMC Nol-Aus & RAM Virtual Bertingkat (ZRAM + Swapfile)

Karena chip eMMC internal memiliki siklus *write endurance* terbatas dan kritis bagi proses boot, arsitektur memori dan logging dirancang untuk **meminimalkan penulisan ke eMMC hingga mendekati 0%**:

1. **Level 1: Memori Virtual ZRAM dengan Kompresi ZSTD (Prioritas 100)**:
   - Alokasi: **ZRAM 1,8 GB (`/dev/zram0`)** dikompresi langsung di dalam RAM fisik memakai algoritma modern **`zstd`** (`PRIO 100`).
   - Rasio kompresi ZSTD berkisar 2,5x–3,2x, melipatgandakan kapasitas RAM 2GB menjadi setara **~4,5 GB RAM virtual instan** dengan latensi 0ms dan **nol keausan flash (nol tulis flash)**.
2. **Level 2: Swapfile Darurat 4 GB pada MicroSD (Prioritas -2)**:
   - Berkas swap dialokasikan sebesar **4 GB pada kartu MicroSD** (`/mnt/storage/swapfile`).
   - Prioritasnya rendah (`PRIO -2`), sehingga hanya tersentuh sebagai *jaring pengaman* darurat bila beban memori melampaui 4,5 GB. eMMC internal tetap 100% aman.
3. **Logging Nol-Aus (`armbian-ramlog` pada `/var/log`)**:
   - Direktori `/var/log` di-mount ke buffer RAM ZRAM terkompresi (`/dev/zram1`).
   - Seluruh tulis log periodik dari journal systemd, daemon, kernel, dan container murni terjadi di RAM, mengeliminasi 99% tulis acak ke eMMC.
   - Pada shutdown bersih, log disinkronkan ke **`/mnt/storage/log`** pada kartu MicroSD (bukan eMMC).
4. **MGLRU Multi-Gen & Sysctl Kernel**:
   - Berkas `/etc/sysctl.d/99-server-opt.conf`:
     ```ini
     vm.swappiness = 60
     vm.vfs_cache_pressure = 50
     vm.dirty_background_ratio = 5
     vm.dirty_ratio = 10
     vm.dirty_writeback_centisecs = 6000
     ```
     Menahan tulis halaman kotor di RAM hingga 60 detik sebelum mem-flush-nya ke disk dalam satu batch, mengurangi keausan flash eMMC.
---

## 6. Mengonfigurasi MicroSD sebagai Penyimpanan Internal Permanen

Agar STB otomatis boot dari eMMC internal dan kartu MicroSD 32GB berfungsi sebagai drive penyimpanan data internal:

### Langkah Eksekusi:
1. Setelah migrasi eMMC selesai, matikan STB (`poweroff`).
2. Lepaskan kartu MicroSD, lalu nyalakan STB. STB akan memboot Armbian 6.12 langsung dari eMMC internal.
3. Setelah masuk via SSH pada eMMC, **masukkan kembali kartu MicroSD** ke slot STB.
4. Jalankan skrip format penyimpanan internal:
   ```bash
   sudo /root/setup_sd_storage.sh
   ```
   *(Atau jalankan perintah berikut manual)*:
   ```bash
   parted -s /dev/mmcblk1 mklabel msdos
   parted -s /dev/mmcblk1 mkpart primary ext4 1MiB 100%
   mkfs.ext4 -F -q -L "SD_STORAGE" /dev/mmcblk1p1
   mkdir -p /mnt/storage
   mount /dev/mmcblk1p1 /mnt/storage
   chown -R <user>:<user> /mnt/storage
   chmod 775 /mnt/storage
   ```
5. Berkas `/etc/fstab` pada eMMC sudah mengikat label `SD_STORAGE` secara otomatis:
   ```text
   LABEL=SD_STORAGE /mnt/storage ext4 defaults,noatime,nodiratime,nofail 0 2
   ```
6. **Arsitektur Offload Total eMMC-ke-MicroSD (Bind-Mount & Docker)**:
   Agar eMMC internal 6,0 GB tidak pernah penuh oleh cache, kode, repositori, dan container Docker:
   - **`/home/<user>` diikat ke MicroSD**:
     ```text
     /mnt/storage/home_<user> /home/<user> none defaults,bind,nofail 0 0
     ```
     Semua berkas pengguna, cache pip/npm, workspace VS Code, dan repositori git otomatis tersimpan langsung pada kartu MicroSD 30 GB.
   - **`/opt` diikat ke MicroSD**:
     ```text
     /mnt/storage/opt /opt none defaults,bind,nofail 0 0
     ```
   - **Docker Root Dir diisolasi pada MicroSD (`/etc/docker/daemon.json`)**:
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
     Semua image Docker, layer container, dan volume otomatis tinggal pada kartu MicroSD. Pengguna `<user>` telah ditambahkan ke grup `docker` sehingga dapat menjalankan `docker run` tanpa `sudo`.
   - **Batas Log Systemd (`/etc/systemd/journald.conf.d/00-cap-size.conf`)**:
     Ukuran log sistem dibatasi maksimal `50M` agar tidak menghabiskan ruang eMMC.
---

## 7. Perbaikan Driver Wi-Fi & Auto-Patch (RTL8189FS) & Bluetooth pada Kernel 6.x

### A. Akar Masalah Teknis Wi-Fi RTL8189FS:
1. **Driver Realtek Out-of-tree**: Realtek tidak pernah menggabungkan modul `8189fs` ke pohon sumber kernel Linux resmi (kernel.org), sehingga kernel Linux 6.x hulu modern tidak menyertakan modul ini secara bawaan.
2. **Perubahan API Linux 6.12 (`set_monitor_channel`)**:
   Kernel 6.12 mengubah tanda tangan callback `set_monitor_channel` pada `cfg80211_ops` dengan menambahkan parameter `struct net_device *dev`. Driver lama gagal dikompilasi dengan galat `incompatible-pointer-types`.
3. **Ketidakcocokan Toolchain GCC 12 vs 15**:
   Kernel Ophub dibangun dengan toolchain GCC 15, yang menyertakan flag `-fmin-function-alignment=4` dan biner `modpost` yang tertaut ke GLIBC 2.38. Pada Debian 12 Bookworm (GCC 12 & GLIBC 2.36), flag ini harus diganti menjadi `-falign-functions=4` dan `modpost` harus dikompilasi ulang secara native.

### B. Akar Masalah Bluetooth B860H:
1. STB ZTE B860H memakai chip Wi-Fi murni (RTL8189FS tanpa Bluetooth terintegrasi).
2. Device tree stok Amlogic P212 / B860H mengaktifkan node hantu Broadcom (`compatible = "brcm,bcm43438-bt"`) pada UART `serial@84c0`.
3. Akibatnya, pada setiap boot kernel mencoba menghubungi chip Broadcom yang tidak ada, memicu timeout `-110` dan menahan boot selama 15 detik.
4. **Perbaikan**: Matikan node hantu tersebut pada DTB (`status = "disabled";`), memangkas waktu boot STB menjadi hanya **12 detik**! Bila butuh Bluetooth, cukup colokkan dongle USB Bluetooth standar yang didukung penuh oleh `btusb`.

### C. Memakai Auto-Patch Turnkey:
Jalankan skrip yang telah kami siapkan pada STB:
```bash
sudo /root/auto_patch_wifi_bt.sh
```
Skrip ini otomatis:
- Mengunduh dan memasang header kernel 6.12.112 dari repositori Ophub.
- Memperbaiki flag Makefile dan mengompilasi `modpost` secara native.
- Mengunduh, menambal untuk API Linux 6.12, dan mengompilasi modul `8189fs.ko`.
- Memasang driver ke `/lib/modules/$(uname -r)/...` dan mengaktifkan auto-load pada `/etc/modules`.
- Mendekompilasi dan menonaktifkan node hantu Broadcom pada DTB eMMC.

---

## 8. Integrasi Tailscale & SSH Tanpa Kata Sandi di Windows

STB tersambung ke mesh VPN Tailscale privat (`<your-tailnet>.ts.net`) dan dikonfigurasi untuk autentikasi SSH berbasis kunci ed25519 tanpa kata sandi:

### A. IP Akses STB:
- **LAN Kabel (`eth0`)**: `<STB-LAN-IP>` (contoh `192.168.1.100`)
- **Wi-Fi Cadangan (`wlan0`)**: `<STB-WIFI-IP>`
- **VPN Tailscale**: `<TAILSCALE-IP>`

### B. Pintasan SSH Windows (`~/.ssh/config`):
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

Anda kini dapat masuk jarak jauh ke STB langsung dari terminal/PowerShell Windows tanpa mengetik kata sandi sama sekali:
```bash
ssh stb       # Akses via LAN kabel
ssh stb-wifi  # Akses via Wi-Fi cadangan
ssh stb-ts    # Akses dari mana saja di luar rumah via Tailscale
```

---

## 9. Skrip Otomasi & Diagnostik Repositori

| Berkas | Fungsi |
| :--- | :--- |
| **`tools/auto_patch_wifi_bt.sh`** | Pengompilasi dan pemasang otomatis driver Wi-Fi RTL8189FS dan pembersih Bluetooth DTB untuk Kernel 6.x. |
| **`tools/diagnostics/ssh_check.sh`** | Rangkaian diagnostik SSH jarak jauh bawaan (Kernel, RAM, Swap, Suhu, Uptime, Wi-Fi, Tata Letak Penyimpanan, Systemd). |
| **`tools/diagnostics/*.sh`** | Skrip diagnostik Bash: `check_optimizations.sh`, `check_bluetooth.sh`, `reboot_and_check.sh`, `install_essentials.sh`. |
| **`tools/optimizations/apply_optimizations.sh`** | Skrip tuning otomatis kernel sysctl, TCP BBR, zram, governor CPU, dan batas journald via SSH. |
| **`tools/download_image.sh`** | Pengunduh image Armbian Ophub (`curl`) + pendekompresi `.img.gz` (`gunzip`). |
| **`tools/flash_sd.py`** | Flasher I/O blok mentah Windows langsung via API Win32 ctypes (`\\.\PhysicalDriveX`) — jalankan `python tools/flash_sd.py` sebagai Administrator. |
| **`boot/meson-gxl-s905x-b860h.dtb`** | Device Tree resmi B860H untuk Linux Kernel 6.x. |

---

## 10. Debugging Perangkat Keras: Pinout Serial UART TTL B860H

Bila STB menemui masalah bootloader (layar hitam / bootloop) atau butuh monitoring level rendah:

![Pinout UART ZTE B860H](assets/b860h_uart_pinout.png)

### Tata Letak Header Pin `X2` (Dekat Lubang Sekrup PCB):
- **Baris Atas**: **`Gnd`** (Ground) $\to$ Sambungkan ke **GND** USB-TTL.
- **Kiri Bawah**: **`Tx`** (Transmit STB) $\to$ Sambungkan ke **RXD** USB-TTL.
- **Kanan Bawah**: **`Rx`** (Receive STB) $\to$ Sambungkan ke **TXD** USB-TTL.
- **VCC**: **JANGAN SAMBUNGKAN** (STB sudah bertenaga dari adapter 12V).

### Monitoring Log Serial Real-time:
```bash
python tools/diagnostics/boot_monitor.py
```
*(Baudrate: `115200`, 8N1, otomatis mendeteksi tiap reboot, stempel waktu + vonis stall. `serial_monitor.py` sebagai tee mentah cadangan).*

---

## 11. Troubleshooting & Playbook: Cold Boot eMMC & Penyimpanan MicroSD

Bab ini mendokumentasikan temuan level perangkat keras yang kritis dan playbook troubleshooting untuk arsitektur penyimpanan ganda (**eMMC Internal + Penyimpanan MicroSD**) pada ZTE B860H:

### A. Masalah 1: Layar Hitam (*Crash*) Akibat Kode Bootstrap x86 pada MicroSD
- **Gejala**: STB mati/membeku seketika pada layar hitam pekat (*blackscreen*) setiap kali kartu MicroSD terpasang saat dinyalakan.
- **Akar Masalah**:
  1. BootROM perangkat keras Amlogic S905X selalu memeriksa slot MicroSD (`MMC 0`) sebelum membaca eMMC (`MMC 1`).
  2. Saat kartu MicroSD diformat dengan perintah Linux `parted mklabel msdos` atau utilitas partisi PC biasa, program tersebut menulis kode bootstrap PC-DOS x86 (`fa b8 00 10...` = instruksi mesin x86 `CLI; MOV AX, 0x1000`) ke byte 0-445 sektor MBR 0.
  3. Karena BootROM S905X berbasis **ARM64 (Cortex-A53)**, ketika prosesor mencoba mengeksekusi byte x86 tersebut, ia langsung mengalami *crash perangkat keras undefined instruction* sebelum sempat mencapai eMMC internal!
- **Perbaikan Sanitasi Sektor 0** (kini otomatis pada `tools/partition_usb_android.py` saat menyiapkan USB Android, atau manual via Git Bash):
  ```bash
  # Nolkan byte bootstrap 0-445, jaga tabel partisi + 0x55AA (X = drive SD, CEK DULU!)
  dd if=/dev/zero of=/dev/sdX bs=1 count=446 conv=notrunc
  ```
  Setelah sanitasi, BootROM Amlogic mengenali kartu MicroSD sebagai *penyimpanan data murni* dan langsung melompat ke eMMC internal.

---

### B. Masalah 2: Layar Hitam (*Hang Cold Boot*) Akibat NVRAM eMMC yang Tak Tersimpan
- **Gejala**: STB reboot hangat (`sudo reboot`) dengan baik, tetapi bila adapter dicabut lalu dicolokkan kembali (*cold boot*), STB menolak boot dan layar monitor tetap hitam pekat.
- **Akar Masalah**:
  1. Skrip resmi `armbian-install` menyalin berkas sistem ke partisi FAT32 eMMC (`mmc 1:1`), tetapi **tidak memperbarui variabel lingkungan U-Boot bawaan (`bootcmd`) pada chip NVRAM eMMC (`0x3ee00000`)**.
  2. Pada cold boot (RAM kosong dari nol), U-Boot mengeksekusi nilai bawaan pabrik:
     ```text
     bootcmd = run storeboot
     storeboot = if imgread kernel boot ${loadaddr}; then bootm ${loadaddr}; fi; run update;
     ```
  3. U-Boot mencari partisi kernel Android lama. Karena Android sudah dihapus oleh Armbian, U-Boot gagal membaca kernel (`Err imgread ... Fmt unsupported`) dan berhenti pada prompt konsol darurat:
     ```text
     gxl_p212_v1#
     ```
  Sambungkan kabel serial USB TTL ke header `X2` (115200 baud). Pada prompt `gxl_p212_v1#`, jalankan:
  ```bash
  setenv bootcmd "if fatload mmc 1:1 0x1020000 emmc_autoscript; then autoscr 0x1020000; fi; if fatload mmc 0:1 0x1020000 s905_autoscript; then autoscr 0x1020000; fi; run storeboot"
  saveenv
  ```
  Perintah `saveenv` menulis konfigurasi ini secara permanen ke chip penyimpanan eMMC (`Writing to MMC(1)... done`). Setelah itu, STB akan boot dengan bootloader mandiri 100% pada setiap *cold boot* dan mati listrik.
  **Catatan implementasi final (STB ini)**: autoscript ditulis ulang secara deterministik (eksplisit `mmc 1:1`, tanpa probing USB/SD, tanpa `saveenv` di dalam; berkas ganda `emmc_autoscript` + `aml_autoscript` di `/boot`, dikompilasi di STB via `mkimage`) dan `bootcmd` disederhanakan sebelum disimpan:
  ```bash
  setenv bootcmd 'fatload mmc 1:1 0x01020000 emmc_autoscript; autoscr 0x01020000'
  saveenv
  ```
  Peringatan: jangan kirim perintah U-Boot yang mengandung `${...}` melalui alat SSH berbasis string (variabel bisa hilang sebelum sampai) — gunakan literal atau sesi serial interaktif/Python.



### C. Masalah 3: Driver Wi-Fi Offline & Penerapan DTB Pre-Built
Agar tidak perlu mengunduh header kernel (~70MB) dan kompilasi manual pada STB baru:
  ```bash
  bash tools/ship_patch.sh stb
  ```
  Wi-Fi langsung aktif dan node hantu Bluetooth dibersihkan dalam **< 2 detik tanpa internet**.
