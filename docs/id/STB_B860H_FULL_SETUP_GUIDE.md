> Terjemahan Bahasa Indonesia dari ../STB_B860H_FULL_SETUP_GUIDE.md (English canonical).
> Kembali ke dokumen Inggris: [STB_B860H_FULL_SETUP_GUIDE.md](../STB_B860H_FULL_SETUP_GUIDE.md)

# Panduan Penyiapan Lengkap B860H: Server Armbian dengan MicroSD sebagai Penyimpanan Internal

Papan: **ZTE ZXV10 B860H V1/V2 (Amlogic S905X, RAM 2 GB, eMMC 8 GB)**.
OS: **Armbian 26.11.0 Bookworm, kernel 6.12.112-ophub (mainline LTS)**.
Peran: server rumahan headless. Kartu MicroSD **bukan** media boot — melainkan
penyimpanan internal permanen (data, swap, home yang di-bind).

Panduan ini mereproduksi penyiapan kerja yang persis pada box ini, dari flashing
hingga auto-patch. Otomasi pendamping ada di `tools/`; diagnostik di
`tools/diagnostics/`.

---

## 0. Arsitektur sekilas

```text
eMMC 7.3 GB (/dev/mmcblk2)
├── p1 511 MB  vfat   BOOT_EMMC      /boot     (kernel, initrd, DTB, autoscript)
└── p2 6.1 GB  ext4   ROOTFS_EMMC    /         (sistem, 3,3 GB bebas)

MicroSD 32 GB (/dev/mmcblk1, satu partisi, ext4, LABEL=SD_STORAGE)
└── p1 29.7 GB  ext4  SD_STORAGE     /mnt/storage
    ├── swapfile            (swap 4 GB, prio -2)
    ├── home_<user>/   --> bind-mount ke /home/<user>
    ├── opt/          --> bind-mount ke /opt
    └── docker/           (DockerRootDir)
```

Jaringan: `eth0` <STB-LAN-IP> (primer, metric 100) · `wlan0` <STB-WIFI-IP>
(cadangan STA, metric 600) · Tailscale <TAILSCALE-IP> · Hotspot `B860H-AP`
(`wlan1`, 192.168.50.1/24 — contoh default AP perangkat, hanya darurat — lihat §8).

Alias SSH pada laptop operator: `ssh stb` (ethernet), `ssh stb-wifi`,
`ssh stb-ts`.

---

## 1. Prasyarat

- MicroSD instalasi ≥ 16 GB (kartu cadangan apa saja; simpan terpisah dari kartu penyimpanan di bawah) + card reader.
- **MicroSD Penyimpanan ≥ 16 GB, berperingkat A1 atau lebih baik** (box ini: 32 GB). Kualitas kartu
  menentukan umur server: I/O acak yang buruk pada kartu murahan membuat seluruh box macet.
  Utamakan kartu endurance/A1; jangan pernah memakai kartu gratisan bawaan gadget.
- Adapter USB TTL (CH340) yang dikabelkan ke header `X2`: Gnd→GND, Tx→RXD, Rx→TXD.
  **Jangan sambungkan VCC** (box bertenaga 12 V).
- Pengaturan serial: **115200 8N1**, teramati sebagai `<COM-PORT>` pada Windows (mis. COM5).

---

## 2. Ambil image Armbian (sumber + praktik terbaik)

Sumber hulu: **rilis GitHub `amlogic-s9xxx-armbian` Ophub**
(`github.com/ophub/amlogic-s9xxx-armbian/releases`). Pilih berkas yang cocok dengan
keempat penanda: **`amlogic_s905x-b860h`** (papan) + **`bookworm`**
(Debian 12) + **`server`** (tanpa desktop) + **`6.12`** (kernel LTS mainline).
Box ini berjalan:
`Armbian_26.11.0_amlogic_s905x-b860h_bookworm_6.12.112_server_2026.10.15.img.gz`.

Praktik terbaik sebelum flashing — verifikasi, lalu tulis:
```bash
bash tools/download_image.sh          # curl + gunzip -> Armbian_b860h.img
# skrip otomatis memverifikasi sha256 bila hulu menerbitkan berkas .sha256
python tools/flash_sd.py             # Jalankan sebagai Administrator (tulis raw Win32)
```
Alternatif: BalenaEtcher / Rufus dengan `.img` yang sama.
Selalu jaga kartu instalasi tetap utuh sampai sistem eMMC terbukti
bisa boot (kartu itu media pemulihan Anda).

---

## 3. Boot pertama dan migrasi ke eMMC

1. Masukkan MicroSD, nyalakan, masuk via SSH (`root` / kata sandi bawaan image).
2. Jalankan instalasi lalu pilih profil B860H:
   ```bash
   sudo armbian-install        # ID box 106 (B860H), filesystem ext4 (1)
   ```
   Ini memasang sistem ke eMMC internal (`BOOT_EMMC` + `ROOTFS_EMMC`).
3. `sudo poweroff`, lepaskan kartu, nyalakan — box kini berjalan dari eMMC.

Berkas boot kritis pada eMMC `/boot/uEnv.txt`:

```ini
LINUX=/zImage
INITRD=/uInitrd
FDT=/dtb/amlogic/meson-gxl-s905x-b860h.dtb
APPEND=root=LABEL=ROOTFS_EMMC rootdelay=5 rootflags=data=writeback rw rootfstype=ext4 console=ttyAML0,115200n8 console=tty0 no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0 max_loop=128 cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory swapaccount=1 video=HDMI-A-1:1920x1080@60e plymouth.enable=0
```

---

## 4. Gunakan ulang MicroSD sebagai penyimpanan internal

Bersihkan kartu menjadi **satu partisi ext4 mentah** (tanpa bootloader, tanpa FAT — jika tidak
BootROM Amlogic memprioritaskannya di atas eMMC), beri label, lalu kaitkan:

1. Pada Linux mana saja (atau STB itu sendiri yang sudah boot dari eMMC *tanpa* kartu):
   partisi seluruh kartu sebagai satu partisi Linux, `mkfs.ext4 -L SD_STORAGE`.
   (Sisa Amlogic USB Burning Tool atau byte bootstrap x86 di sektor 0
   membuat BootROM crash — nolkan byte 0–445 bila kartu dipartisi oleh
   perkakas Windows: `dd if=/dev/zero of=/dev/sdX bs=1 count=446 conv=notrunc`.)
2. Tambahkan ke `/etc/fstab` (semua mount yang didukung SD memakai `nofail` agar box tetap
   boot dengan kartu dilepas):

```fstab
LABEL=BOOT_EMMC       /boot        vfat    defaults 0 2
LABEL=ROOTFS_EMMC     /            ext4    defaults,noatime,nodiratime,commit=600,errors=remount-ro 0 1
tmpfs                 /tmp         tmpfs   defaults,nosuid 0 0
/mnt/storage/swapfile none        swap    sw,nofail 0 0
LABEL=SD_STORAGE      /mnt/storage ext4    defaults,noatime,nodiratime,nofail 0 2
/mnt/storage/home_<user> /home/<user> none defaults,bind,nofail 0 0
/mnt/storage/opt /opt none        defaults,bind,nofail 0 0
```

3. Buat direktori pendukung dan swapfile pada kartu:
   ```bash
   sudo mkdir -p /mnt/storage/{home_<user>,opt,docker,data}
   sudo dd if=/dev/zero of=/mnt/storage/swapfile bs=1M count=4096
   sudo chmod 600 /mnt/storage/swapfile && sudo mkswap /mnt/storage/swapfile
   sudo mount -a && sudo swapon -a
   ```
   Hasil: ~22 GB bebas pada `/mnt/storage`, swapfile 4 GB (prio -2) di bawah
   zram 1,8 GB (prio 100).
   Praktik terbaik SD-sebagai-internal (mengapa dibangun seperti ini):
   - Satu partisi, tanpa bootloader/FAT: BootROM selalu memprobe slot lebih dulu;
     apa pun yang tampak bisa-boot di sana membajak boot. `nofail` di mana-mana agar
     SD yang mati/dilepas tidak pernah menghalangi boot.
   - `noatime,nodiratime,commit=600` + jurnal yang dibatasi: memangkas amplifikasi tulis SD
     secara dramatis; kartu kebanyakan hanya melihat tulis media sekuensial.
   - Swap pada SD adalah pilihan terakhir (prio -2 di bawah zram prio 100): dengan
     RAM 1,8 GB + zram, swapfile SD hampir tidak pernah tersentuh, sehingga aus
     bisa diabaikan — tetapi ia menyelamatkan box dari OOM killer saat lonjakan.
   - Kartu SD tidak punya TRIM: jangan pernah `fstrim` kartu (fstrim mingguan `fstrim.timer`
     hanya bermanfaat bagi eMMC); saat kartu menua, ganti saja — sistem dan data
     memang dirancang terpisah (`/home`, `/opt`, `/mnt/storage`, Docker).


---

## 5. Auto-patch: driver Wi-Fi dan perbaikan Bluetooth DTB

Image stok Ophub tidak menyertakan driver RTL8189FS out-of-tree dan memuat
node Broadcom-BT hantu yang membuat boot macet 15 dtk. Satu perintah dari laptop,
tanpa kompilasi di sisi STB:

```bash
bash tools/ship_patch.sh stb
```

Fungsinya (`tools/auto_patch_wifi_bt.sh` + `packages/b860h_patch/`):
- Memasang `8189fs.ko` prebuilt (3,05 MB) untuk kernel 6.12.112.
- Memasang `meson-gxl-s905x-b860h.dtb` (40,8 KB) dengan node BT hantu dimatikan.
- Wi-Fi menyala dalam < 2 dtk tanpa lalu lintas internet.

---

## 6. Boot deterministik (perbaikan untuk prompt `gxl_p212_v1#`)

U-Boot vendor (`bootcmd=run storeboot`) **tidak memiliki hook** untuk skrip boot eMMC:
pada cold boot ia mencoba partisi Android (yang sudah dihapus), memindai SD/USB untuk
recovery, lalu berhenti di prompt `gxl_p212_v1#`. Perbaikan yang diterapkan pada box ini:

1. `/boot/emmc_autoscript` + `/boot/aml_autoscript` — skrip deterministik,
   dikompilasi **di STB** dengan `mkimage` (jangan pernah di Windows: CRLF dan
   `${...}` yang dimodifikasi shell merusaknya). Isinya sepenuhnya literal (tanpa variabel U-Boot
   sama sekali — U-Boot ini mengekspansi `${...}` di dalam skrip `autoscr`
   secara prematur, yang diam-diam mengosongkannya):
   ```text
   setenv bootargs root=LABEL=ROOTFS_EMMC ... (baris APPEND penuh, literal)
   fatload mmc 1:1 0x11000000 /zImage
   fatload mmc 1:1 0x15000000 /uInitrd
   fatload mmc 1:1 0x1000000 /dtb/amlogic/meson-gxl-s905x-b860h.dtb
   booti 0x11000000 0x15000000 0x01000000
   ```
   Sumbernya ada di repo pada `boot/emmc_autoscript.cmd`
   (salinan identik-byte dipakai untuk kedua berkas).
2. NVRAM kini boot langsung ke sana (satu kali, terverifikasi UART):
   ```text
   setenv bootcmd 'fatload mmc 1:1 0x01020000 emmc_autoscript; autoscr 0x01020000'
   saveenv   # Writing to MMC(1)... done
   ```

Pemulihan bila boot pernah jatuh ke prompt: interupsi autoboot (tombol spasi),
jalankan lima baris di atas manual, lalu periksa.

---

## 7. Kebijakan konsol HDMI (headless-light secara bawaan)

`tools/hdmi-console.sh` + aturan udev `tools/99-hdmi-console.rules`,
terpasang di `/usr/local/bin/hdmi-console.sh` dan
`/etc/udev/rules.d/99-hdmi-console.rules`, plus unit oneshot
`hdmi-console-boot.service` agar kebijakan juga berlaku saat boot.

- HDMI tercolok (EDID ada) → unblank framebuffer, `getty@tty1` berjalan.
- HDMI tercabut (EDID kosong) → output diblankan, `getty@tty1` dihentikan.
- CATATAN: driver meson selalu melaporkan `status=connected` (flag `video=...e`
  memaksa konektor menyala), sehingga kehadiran dideteksi via EDID, bukan status.

---

## 8. Hotspot dan failover darurat

- Profil `B860H-AP` (SSID `B860H-AP`, WPA2, 192.168.50.1/24 pada `wlan1` — contoh default AP perangkat).
  STA (`wlan0`, Wi-Fi rumah) dan AP berjalan bersamaan pada satu radio RTL8189FS
  — sudah terverifikasi berfungsi.
- Keadaan bawaan: hotspot **mati** (`autoconf=no`). Cakupan darurat bersifat
  otomatis: `tools/hotspot-failover.sh` (tiap 1 mnt via
  `hotspot-failover.{service,timer}`) menyalakan AP setelah dua kegagalan ping
  uplink berturut-turut dan mematikannya saat uplink pulih.
- SSH darurat saat LAN mati: gabung ke `B860H-AP` (kata sandi
  `<hotspot-password>`), lalu `ssh <user>@192.168.50.1`.
  Ganti kata sandinya dengan:
  `nmcli con mod B860H-AP wifi-sec.psk <kata-sandi-baru>`.

---

## 9. Baseline server dan optimasi yang diterapkan

- SSH (autentikasi kunci), Docker (root dir di SD), Tailscale, swap+zram, ramlog ala-log2ram,
  jurnal dibatasi 50 MB, rsyslog dibuang, BBR + fq, governor `schedutil`,
  scheduler SD `none` (persisten-udev), eMMC `mq-deadline`,
  swappiness 100 (benar dengan zram sebagai swap utama), tumpukan Bluetooth dimask
  (tidak ada perangkat keras BT pada papan ini).
- Diterapkan via `tools/optimizations/apply_optimizations.sh`;
  delta spesifik-host ada di `/etc/sysctl.d/99-server-opt.conf`,
  `/etc/udev/rules.d/60-iosched.rules`, `/etc/systemd/journald.conf.d/`.

---

## 10. Matriks verifikasi (semua lolos pada box ini)

| Uji | Hasil |
|---|---|
| Soft reboot (`sudo reboot`) | Hands-off hingga login, 0 layanan gagal |
| Cold boot (cabut → colok daya) | Hands-off hingga login, dengan dan tanpa HDMI |
| HDMI tercolok | Prompt login pada TV |
| HDMI tercabut | Output blank, getty berhenti, ~300 MB RAM terpakai |
| Wi-Fi STA + AP bersamaan | STA terasosiasi (rssi 80%+) sementara AP memancar |
| Failover hotspot | AP menyala setelah uplink hilang, mati saat pulih (diuji dengan blok ICMP) |
| Docker | `hello-world` berjalan (image ARM) |
| Kesehatan eMMC | 2,7/6,0 GB terpakai; tanpa kernel basi; timer fstrim aktif |

Pantau boot apa pun secara live dari laptop:
```bash
python tools/diagnostics/boot_monitor.py --dir logs
```
Ia otomatis mendeteksi setiap reboot, memberi stempel waktu pada tiap baris, dan menutup tiap log boot
dengan vonis (`OK login t+...`, `STOPPED di prompt U-Boot`, `STUCK ...`).

---

## 11. Catatan pemeliharaan

- **Jangan pernah edit `/boot/*.cmd` di Windows** — kompilasi di STB dengan `mkimage`
  (`cat -A` berkasnya dulu: baris harus berakhir `$`, bukan `^M$`).
- **Jangan pernah kirim `${...}` U-Boot melalui alat SSH berbasis string** — isinya bisa
  hilang sebelum mencapai U-Boot. Gunakan perintah literal atau sesi serial
  (`tools/diagnostics/uboot_interactive.py`, `auto_restore_linux.py`).
- Jaga kartu SD sebagai satu partisi ext4; jangan pernah taruh bootloader di atasnya.
- `packages/b860h_patch/` adalah bundel patch offline; `tools/ship_patch.sh`
  menyebarkannya. `tools/vendor/` menampung `ampack.exe` Amlogic yang opaque.
- Konvensi penuh repo: bash+ssh untuk perintah STB, Python hanya untuk
  serial-UART, parsing biner, atau I/O raw-disk Windows.
- SOP pembaruan kernel (`armbian-update -k <ver> -u stable`): updater membutuhkan
  `setenv initrd_addr 0x15000000` di `/boot/emmc_autoscript.cmd` (sudah ada
  sejak 2026-10-26); bila instal ulang pakai `-b no` (cadangan sudah di `/ddbr`);
  setelah setiap pembaruan patch ulang DTB + bangun ulang `8189fs` (alur `tools/ship_patch.sh`),
  lalu reboot dan verifikasi `wlan0`. Detail: `SUMMARY_OF_WORK.md` §8.
