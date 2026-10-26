> Terjemahan Bahasa Indonesia dari ../SELF_HEALING_BOOT.md (English canonical).
> Kembali ke dokumen Inggris: [SELF_HEALING_BOOT.md](../SELF_HEALING_BOOT.md)

# Boot Mandiri-Pulih — Tinjauan Teknis B860H

Tujuan: setiap pembaruan/kegagalan di masa depan bisa boot tanpa UART. UART tetap ada sebagai pilihan terakhir, bukan sebagai prosedur.

## Rantai boot dan peta titik-gagal-tunggal (SPOF)

| Tahap | Pemilik | Cara gagal | Pemulihan mandiri | Sisa risiko |
|---|---|---|---|---|
| BootROM → SPL → U-Boot | Sektor eMMC 0–4MB (turunan HG680P, terverifikasi selisih 26B MBR) | Kematian eMMC, flash buruk | Bypass SD via suntik sektor mentah (`patch_uboot.py`) | Butuh SD fisik + siklus daya. eFuse keynum=4: hanya rantai bertanda yang boot, jangan pernah flash ulang membabi buta. |
| Env NVRAM (`0x3ee00000`, AES-opaque) | Satu baris `bootcmd` | Kehilangan env → jalan buntu `run storeboot` (terbukti: storeboot tidak memprobe berkas apa pun, `storeboot_probe.log`) | Tidak ada yang bisa dilakukan di dalam env vendor (path bawaan tidak memuat apa pun). Pencegahan: nol `saveenv` di masa depan; logika fallback tinggal di berkas, bukan di env. | Satu baris NVRAM tetap ada. Pemulihan UART terdokumentasi (`uart_shell.py`). |
| Autoscript | /boot, mkimage di-STB | Edit buruk, CRLF | Blok fallback, tanpa env, tanpa kondisional. TERBUKTI 2026-10-26: primer dihapus, slot .good boot, login t+34,5 dtk. | Primer yang tertulis separuh plus `booti` di atas sampah bisa hang; SOP snapshot mengatasinya. |
| Kernel/initrd/DTB | deb + updater | Kernel baru panik, regresi DTB, `.ko` salah vermagic | Slot A/B: set `.good` dipromosikan sebelum pembaruan; blok fallback membootnya. Userspace mendeteksi kernel asing via `uname -r` vs `/boot/.expected_kernel`. | Boot pertama kernel baru tetaplah ujiannya. Jangan pernah hapus `.good` sebelum set baru terverifikasi. |
| Userspace/layanan/jaringan | systemd, NM, Tailscale, Docker | Hang saat shutdown/reboot, layanan gagal | `RuntimeWatchdogSec=30` + `ShutdownWatchdogSec=5min` (`meson_gxbb_wdt`, bawaan) memaksa reset perangkat keras. Failover hotspot menutup kehilangan uplink. | Watchdog butuh userspace yang masih cukup hidup untuk memberi makan (petting) (petting kernel). Hang di prompt U-Boot di luar cakupan (tidak ada WDT di sana). |
| Rootfs/penyimpanan SD | ext4, fstab `nofail` | SD mati, fs rusak | `nofail` di mana-mana membuat boot tetap jalan tanpa SD; bind mount terdegradasi, sistem selamat. `fsck.fix=yes` pada cmdline. | Data di SD yang mati tetap butuh penggantian fisik. |

## SOP Pembaruan (urutan wajib)

1. `tools/snapshot_boot_good.sh` — promosikan set berjalan menjadi `.good`, tulis `/boot/.expected_kernel`.
2. `armbian-update -k <ver> -u stable` (dengan `-b no` bila instal ulang).
3. Patch ulang DTB + bangun ulang `8189fs` (alur ship_patch); segarkan `packages/b860h_patch/`.
4. Reboot, verifikasi `uname -r` == yang diharapkan + `wlan0` + nol layanan gagal.
5. Hanya setelah set baru terbukti baik — jalankan ulang snapshot untuk mempromosikannya.

## Arti konkret "tanpa UART"

- Kernel baru panik → fallback U-Boot memboot `.good` → SSH/Tailscale menyala pada kernel lama → perbaiki dari jauh.
- Hang saat shutdown/reboot → watchdog perangkat keras mereset SoC.
- Kegagalan layanan/jaringan → failover + watchdog + SSH jarak jauh.
- Kehilangan env / kerusakan bootloader → UART (risiko sisa yang diterima; probabilitas diminimalkan, perkakas pemulihan tersedia).
