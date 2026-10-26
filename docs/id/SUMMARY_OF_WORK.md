> Terjemahan Bahasa Indonesia dari ../SUMMARY_OF_WORK.md (English canonical).
> Kembali ke dokumen Inggris: [SUMMARY_OF_WORK.md](../SUMMARY_OF_WORK.md)

# Ringkasan Kerja: Pemulihan ZTE ZXV10 B860H dan Bypass eMMC

Dokumen ini merangkum seluruh investigasi, perbaikan arsitektural, restrukturisasi repositori, dan modifikasi konfigurasi yang diselesaikan untuk memboot Linux Armbian (Kernel 6.x+) pada TV Box ZTE B860H V1/V2 (Amlogic S905X) dengan eMMC internal yang mati/rusak.

---

## 1. Arsitektur Inti & Masalah yang Diselesaikan

### A. Loop Boot & Penulisan eMMC
- **Masalah**: Skrip boot Armbian bawaan (`aml_autoscript`) memeriksa dan menyimpan keadaan lingkungan boot memakai perintah U-Boot `saveenv`. Ketika flash eMMC onboard mati atau rusak, penulisan ke NVRAM-nya gagal atau hang, menyebabkan U-Boot reboot dalam loop tak berujung.
- **Perbaikan**: Mengganti `aml_autoscript` bawaan dengan skrip bypass kustom. Skrip ini langsung memuat kernel `Image`, `uInitrd`, dan `FDT` dari kartu SD memakai `fatload` lalu boot via `booti` seketika. Ia melewatkan semua penyimpanan NVRAM (`saveenv`) dan parameter reboot, sehingga loop boot terhenti.

### B. Relokasi Kernel (TrustZone Sync Abort)
- **Masalah**: Kernel Linux mainline (v5.8+) memakai `text_offset` bawaan `0` pada headernya. Ketika U-Boot vendor lawas menghitung alamat relokasi (`DRAM_BASE + text_offset`), ia mencoba memuat kernel langsung ke alamat `0x0`. 16MB pertama DRAM dicadangkan untuk TrustZone Secure Monitor (BL31). Menulis ke sana memicu `Synchronous External Abort` (ESR `0x96000210`) di level perangkat keras, mereset papan.
- **Perbaikan**: Menulis dan menerapkan `patch_image_header.py` untuk mengubah medan `text_offset` pada offset byte 8 di berkas kernel `Image` menjadi `0x1080000` (16,5 MB). Ini memindahkan titik muat kernel dengan aman ke atas batas Secure World 16MB.

### C. Ketidakcocokan GPIO Wi-Fi (Realtek RTL8189FS)
- **Masalah**: Device Tree Blob (DTB) generik referensi `p212` memetakan pin reset daya Wi-Fi (`sdio-pwrseq`) ke Pin GPIO `85`. Tata letak papan ZTE B860H justru menyambungkan pin reset itu ke Pin GPIO `76`. Akibatnya modul Wi-Fi tetap mati dan tak terlihat oleh bus SDIO.
- **Perbaikan**: Merefactor `patch_dtb.py` agar mengurai struktur berkas DTB secara dinamis. Skrip memindai struktur device tree, menemukan properti `reset-gpios` pada node `sdio-pwrseq`, dan mengubah pin reset dari `85` (`0x55`) menjadi `76` (`0x4c`) secara in-place.

---

## 2. Restrukturisasi Repositori

Ruang kerja dirapikan dari direktori akar yang berantakan menjadi tiga direktori logis agar mudah dipelihara dan mengikuti standar kode bersih:

```text
<repo-checkout>/
├── boot/                        # Skrip boot aktif (terkompilasi + sumber)
│   ├── aml_autoscript           # Autoscript boot-langsung terkompilasi
│   ├── aml_autoscript.cmd       # Kode sumber skrip
│   ├── emmc_autoscript          # Skrip boot eMMC deterministik terkompilasi
│   └── emmc_autoscript.cmd      # Kode sumber skrip
├── firmware/                    # Biner bootloader, DTB stok, set unbrick lawas
│   ├── legacy/                  # Utilitas flashing lawas dan berkas param
│   │   └── usb-unlock/          # Berkas unlock USB lawas
│   ├── uboot_B860H-emmc-stock.bin # U-Boot khusus-eMMC stok B860H (blob terenkripsi, referensi)
│   ├── uboot_HG680P-sdboot.bin    # U-Boot berkemampuan SD-boot (dipakai patch_uboot.py / do_dd.sh)
│   └── meson-gxl-s905x-p212-stock-unpatched.dtb # DTB referensi stok (pin Wi-Fi 85)
├── tools/                       # Skrip flashing, patching, dan optimasi
│   ├── diagnostics/             # Monitor serial, dumper, skrip pengecekan
│   │   ├── find_gpio_offset.py  # Memindai offset DTB secara dinamis
│   │   └── serial_monitor.py    # Monitor port UART live (bawaan <COM-PORT>)
│   ├── optimizations/           # Konfigurasi governor dan optimasi sistem
│   ├── patch_uboot.py           # Menyuntikkan U-Boot kustom ke sektor SD
│   ├── patch_dtb.py             # Menambal GPIO reset Wi-Fi
│   ├── patch_image_header.py    # Menambal offset muat kernel
│   └── do_dd.sh                 # Skrip shell suntikan sektor
├── docs/                        # Berkas panduan dan riset lengkap
│   ├── EMMC_BYPASS_RESEARCH.md  # Laporan riset mendalam soal ATF & BootROM
│   ├── RESEARCH_AND_RECOVERY_GUIDE.md  # Panduan persiapan kartu SD langkah demi langkah
│   └── SUMMARY_OF_WORK.md       # Ringkasan kerja ini
└── live_boot.log                # Log serial live
```

---

## 3. Validasi dan Modifikasi Kartu SD

Ketika kartu SD di-mount di Windows, kami menjalankan pemeriksaan diagnostik dan menerapkan patch yang diperlukan:

1. **Image Kernel (`Image`)**:
   - Terdeteksi `text_offset` bawaan `0x0`.
   - Menjalankan `patch_image_header.py` dan berhasil memperbarui offset header menjadi `0x1080000`.
2. **Device Tree (`dtb\amlogic\meson-gxl-s905x-p212.dtb`)**:
   - Memetakan node DTB secara dinamis dan menemukan properti pin reset daya Wi-Fi pada offset `28256` (`0x6e60`).
   - Menjalankan `patch_dtb.py` dan berhasil memperbarui nilai pin reset dari `85` menjadi `76`.
3. **Autoscript (`aml_autoscript`)**:
   - Menemukan kartu SD memakai skrip multi-boot yang rawan reboot.
   - Menggantinya dengan versi boot-langsung `boot/aml_autoscript`.
4. **Konfigurasi Boot (`uEnv.txt`)**:
   - Membaca tabel partisi image yang dipatch memakai python, menemukan superblock ext4 Partisi 2, dan memverifikasi UUID-nya.
   - Memverifikasi bahwa `uEnv.txt` terkonfigurasi benar dengan `root=UUID=<uuid-rootfs-anda>`.

---

## 4. Status Saat Ini & Verifikasi
Semua berkas pada kartu SD kini telah dipatch dan terverifikasi penuh. Langkah berikutnya adalah mencolokkan kembali kartu SD ke papan B860H, menyambungkan adapter UART, dan memboot sistem.

---

## 5. Komisioning Perangkat Keras Baru: Armbian 6.12 Modern, Pembersihan PPPwn, Migrasi eMMC & Penyiapan Penyimpanan SD

Unit perangkat keras ZTE ZXV10 B860H baru yang sehat diperoleh untuk menggantikan unit lama dengan eMMC perangkat keras yang mati. Unit baru ini awalnya di-flash penjual pasar dengan `STB-Pwn` (dongle jailbreak PS4 PPPwn). Kami mengeksekusi overhaul ujung-ke-ujung:

### A. Audit Keamanan & Pembersihan PPPwn
- **Akses Awal**: Mendapat shell root via UI web Nginx/PHP-FPM tanpa autentikasi peninggalan penjual pada port 80 yang berjalan dengan `www-data ALL=(ALL) NOPASSWD: ALL` di sudoers.
- **Artefak yang Dibersihkan**: Menyingkirkan daemon `pipwn`, `pppoe`, `dtlink`, mematikan proses `pppwn64` yang berjalan, membersihkan paket Nginx dan PHP, serta membersihkan `/etc/rc.local`.
- **Membersihkan Partisi `/boot`**: Menghapus puluhan MB APK sisa penjual dan rekaman `FSCK*.REC` rusak yang memenuhi partisi boot FAT 122MB.
- **Penyiapan Kredensial**: Mengatur kata sandi untuk `root` dan membuat pengguna administratif `<user>` (ganti dengan `<stb-password>` milik Anda).

### B. Penerapan Armbian 6.12 LTS Modern
- **Image Terpilih**: `Armbian_26.11.0_amlogic_s905x-b860h_bookworm_6.12.112_server_2026.10.15` (Debian 12 Bookworm, Kernel 6.12.112 LTS oleh Ophub).
- **Flashing Turnkey via Windows**: Menulis `tools/download_and_prep_image.py` (mengunduh dan mendekompresi image mentah 3,5GB) dan `tools/flash_sd.py` (penulisan blok langsung via API Win32 ctypes ke drive fisik pada level kilobyte per detik dua digit).
- **Perbaikan Timeout Initramfs**: Mengatasi `ALERT! UUID=... tidak ada` dengan mengonfigurasi `root=LABEL=ROOTFS rootdelay=10` pada `uEnv.txt`.

### C. Migrasi Penuh ke eMMC (`armbian-install`)
- Menjalankan `armbian-install` dengan ID Box `106` (`B860H`, `meson-gxl-s905x-b860h.dtb`).
- Mempartisi eMMC internal (`/dev/mmcblk2`) dengan partisi boot 512MB modern (`BOOT_EMMC`) dan root filesystem 6,1GB (`ROOTFS_EMMC`).

### D. Memori Virtual Swap & Alih Fungsi Penyimpanan SD
- **Memori Virtual**: Membuat `/swapfile` persisten 2GB pada root eMMC, mengonfigurasi `/etc/fstab`, dan menerapkan tuning sysctl (`vm.swappiness=60`, `vm.vfs_cache_pressure=50`).
- **Alih Fungsi MicroSD**: Memformat kartu MicroSD 32GB (`/dev/mmcblk1`) menjadi satu partisi ext4 (`SD_STORAGE`) via `/root/setup_sd_storage.sh`.
- **Auto-mount & Symlink**: Mengikat `LABEL=SD_STORAGE` ke `/mnt/storage` dengan `nofail` pada `/etc/fstab`, dan membuat symlink pengguna langsung `/home/<user>/storage`.
- **Endpoint Aktif**: Terverifikasi STB berjalan bersih pada `<STB-LAN-IP>` (contoh `192.168.1.100`) dengan nol layanan systemd gagal dan suhu CPU 36°C.

---

## 6. Docker CE, Offloading Total ke SD, Tailscale Mesh & Perkakas SSH Bawaan

### A. Offloading eMMC Total (Bind-Mount)
- Memindahkan `/home/<user>` dan `/opt` sepenuhnya ke kartu MicroSD 30GB (`/mnt/storage`) via bind-mount `/etc/fstab`.
- Mengonfigurasi pembatasan log journald systemd (`MaxUse=50M`) dan pembersihan otomatis cache paket APT (`APT::Keep-Downloaded-Packages "false"`).
- eMMC internal 8GB (`/dev/mmcblk2p2`, rootfs 6,1GB) mempertahankan **3,7 GB ruang bebas (39% terpakai)** secara permanen.

### B. Docker CE & Docker Compose
- Memasang Docker CE resmi dan plugin Docker Compose pada ARM64.
- Mengonfigurasi root daemon Docker ke MicroSD (`"data-root": "/mnt/storage/docker"` pada `/etc/docker/daemon.json`), memastikan semua image, layer, dan volume tinggal di kartu SD.
- Menambahkan `<user>` ke grup `docker` agar eksekusi container tanpa kata sandi.

### C. Failover Wi-Fi & Routing Jaringan
- Memperbaiki driver out-of-tree Realtek RTL8189FS untuk Kernel Linux 6.12 via `tools/auto_patch_wifi_bt.sh` dan menonaktifkan Bluetooth Broadcom hantu pada DTB.
- Mengonfigurasi routing failover otomatis: Ethernet `eth0` pada `metric 100` (Primer 100 Mbps) dan Wi-Fi `wlan0` pada `metric 600` (cadangan mulus, `powersave: off`).

### D. Tailscale Mesh & SSH Bawaan Tanpa Kata Sandi
- Memasang Tailscale pada STB (`<TAILSCALE-IP>`) yang tersambung ke `<your-tailnet>.ts.net`.
- Mendaftarkan kunci publik ED25519 Windows ke `authorized_keys` STB.
- Menambahkan pintasan pada `~/.ssh/config` (`ssh stb`, `ssh stb-wifi`, `ssh stb-ts` dengan HostName placeholder masing-masing).
- Memigrasi seluruh perkakas diagnostik dan optimasi dari Python/Paramiko ke skrip Bash bawaan (`tools/diagnostics/*.sh`, `tools/optimizations/*.sh`), menghilangkan dependensi Python eksternal.

---

## 7. Resolusi Blackscreen Cold Boot, Persistensi NVRAM U-Boot & Paket Offline

### A. Jebakan Crash MBR x86 pada MicroSD
- **Masalah**: Saat memformat kartu MicroSD dengan `parted mklabel msdos`, kode mesin bootstrap x86 standar ditulis ke sektor 0 (byte 0–445). Karena BootROM perangkat keras Amlogic memprioritaskan slot MicroSD di atas eMMC, prosesor ARM64 Cortex-A53 mencoba mengeksekusi instruksi x86, memicu crash instruksi ilegal sebelum eMMC terprobe.
- **Perbaikan**: Nolkan byte 0–445 sambil menjaga tabel partisi (byte 446–509) dan tanda `0x55AA`, memungkinkan fallback bersih BootROM ke eMMC (awalnya `tools/sanitize_sd_mbr.py`, kini dilipat ke `tools/partition_usb_android.py`; padanan manual: `dd if=/dev/zero of=/dev/sdX bs=1 count=446 conv=notrunc`).

### B. Resolusi NVRAM `bootcmd` U-Boot eMMC
- **Masalah**: Skrip `armbian-install` mengisi partisi boot FAT32 (`mmc 1:1`), tetapi membiarkan lingkungan NVRAM U-Boot vendor (`0x3ee00000`) tak tersentuh (`bootcmd=run storeboot`). Pada cold boot, U-Boot jatuh ke prompt interaktif `gxl_p212_v1#` karena kernel Android hilang, menyebabkan layar hitam persisten pada HDMI.
- **Perbaikan**: Menangkap shell U-Boot live via UART perangkat keras `X2` (port serial, 115200 baud — mis. `<COM-PORT>` di Windows) dan mengomit sekuens autoboot secara permanen ke NVRAM eMMC via `saveenv`:
  ```bash
  setenv bootcmd "if fatload mmc 1:1 0x1020000 emmc_autoscript; then autoscr 0x1020000; fi; if fatload mmc 0:1 0x1020000 s905_autoscript; then autoscr 0x1020000; fi; run storeboot"
  saveenv
  ```
  **Refactor lanjutan**: autoscript ditulis ulang secara deterministik (eksplisit `mmc 1:1`, tanpa probing USB/SD, tanpa `saveenv` di dalam; berkas ganda `emmc_autoscript` + `aml_autoscript`, dikompilasi di STB via `mkimage`) dan `bootcmd` disederhanakan menjadi `fatload mmc 1:1 0x01020000 emmc_autoscript; autoscr 0x01020000` sebelum `saveenv`. Pelajaran: jangan pernah kirim perintah U-Boot berisi `${...}` melalui perkakas SSH berbasis string (variabel bisa hilang sebelum sampai) — gunakan literal atau sesi serial interaktif/Python.


### C. Paket Patch Offline Pre-Built (`packages/b860h_patch/`)
- Mengekstrak biner produksi yang telah teruji langsung dari STB live:
  - `packages/b860h_patch/8189fs.ko` (3,05 MB)
  - `packages/b860h_patch/meson-gxl-s905x-b860h.dtb` (40,8 KB)
- Membuat instalasi turnkey `packages/b860h_patch/install.sh` dan skrip penerapan host `tools/ship_patch.sh` untuk patching Wi-Fi & Bluetooth offline instan pada unit yang baru dipasang tanpa mengunduh atau mengompilasi.

---

## 8. Insiden Pembaruan Kernel 6.12.112 → 6.12.114 (2026-10-26)

### A. Kehilangan NVRAM `bootcmd` → Box Mati
- **Masalah**: Setelah `armbian-update -k 6.12.114`, box tidak pernah kembali (tanpa LAN, tanpa Tailscale, `last seen` Tailscale beku pada reboot updater). UART menunjukkan U-Boot berhenti setelah autoboot tanpa `reading emmc_autoscript`; pemeriksaan interaktif mengonfirmasi `bootcmd=run storeboot` (env bawaan) pada `gxl_p212_v1#`. `bootcmd` deterministik yang tersimpan hilang; sektor env `0x3ee00000` terbaca sebagai entropi tinggi (konsisten dengan env terenkripsi AES vendor — korupsi vs tertimpa tak dapat dibedakan dari Linux). Kesehatan eMMC baik (`pre_eol_info 0x01`, `life_time 0x01`); jurnal bersifat ramlog-volatile sehingga shutdown tidak meninggalkan jejak.
- **Perbaikan**: Mengembalikan `setenv bootcmd 'fatload mmc 1:1 0x01020000 emmc_autoscript; autoscr 0x01020000'` + `saveenv` via UART (catcher `logs/uart_shell.py`), box boot 6.12.114 hands-off (terverifikasi lewat siklus reboot kedua).

### B. Path Boot Bawaan Vendor Terbukti Jalan Buntu
- `run storeboot` ditangkap live via UART (`logs/storeboot_probe.log`, catcher `logs/uart_catch.py`): imgread logo gagal → cek USB-burn → cek SD → pindai penyimpanan USB (`Bad device usb 0`) → prompt. Ia tidak pernah memprobe autoscript apa pun (`s905`/`aml`/`boot.ini`/`fatload` absen dari trace). Menaruh berkas tidak dapat menyelamatkan box ber-env bawaan; hanya NVRAM `bootcmd` (atau U-Boot kustom residen di belakangnya) yang memboot unit ini.

### C. Identitas Bootloader Live eMMC Tuntas
- `dd` wilayah bootloader eMMC (`/tmp/bl.dump`, disimpan di `logs/bl-emmc-live.dump`, sha256 `bd3cb4a5…`) vs `firmware/uboot_HG680P-sdboot.bin`: identik kecuali **26 byte pada `0x1ba–0x1ff`** (area tabel partisi MBR). Bootloader eMMC MEMANG biner turunan HG680P, bukan build stok B860H terpisah. Payload terenkripsi/terkompresi (Rizin `iz` hanya menghasilkan noise; `strings` polos tidak menemukan apa-apa) — analisis statis butuh unpacker sadar-FIP atau image runtime terdekripsi.
- `[EFUSE_MSG] keynum is 4` terkonfirmasi pada log boot: rantai secure utuh, penggantian bootloader eMMC tetap terlarang; chainload RAM (`u-boot.ext` via `go`) tetap menjadi path U-Boot kustom yang aman.

### D. Keanehan `armbian-update` (Ophub, Okt 2026)
- Percobaan pertama bisa gagal sementara pada cek `curl github.com`-nya (tanpa skema) — coba ulang biasanya berhasil.
- `update_initrd_addr` gagal keras bila `/boot/emmc_autoscript.cmd` kekurangan `setenv initrd_addr`: ditambahkan baris kompat `setenv initrd_addr 0x15000000` (tak dipakai saat boot, alamat literal tidak berubah) ke `boot/emmc_autoscript.cmd` + kembaran STB, dikompilasi ulang di-STB via `mkimage`.
- Path instal ulang butuh `-b no` (langkah cadangan mencari berkas `-6.12.112` yang tergantikan); cadangan penuh sudah ada di `/ddbr/backup/6.12.112`.
- Wajib pasca-pembaruan: patch ulang DTB (stok kembali, node BT hantu kembali) + bangun ulang `8189fs` terhadap header baru (`tools/auto_patch_wifi_bt.sh` dikirim via `scp`, berjalan di-STB). Menyegarkan `packages/b860h_patch/` ke 6.12.114 (`8189fs.ko` vermagic `6.12.114-ophub`, DTB 40925 B terpatch).
