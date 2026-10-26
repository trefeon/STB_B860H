> Terjemahan Bahasa Indonesia dari INDEX (English canonical: tidak ada; indeks khusus-ID).
> Kembali ke dokumen Inggris: [README.md](../../README.md) · [docs/](../)

# Indeks Dokumentasi Bahasa Indonesia

Seluruh berkas di direktori ini adalah cermin Bahasa Indonesia dari dokumen Inggris kanonis. Nama berkas dipertahankan identik agar mudah di-diff; isi diterjemahkan ke Bahasa Indonesia yang natural. Blok kode, perintah, nama DTB/U-Boot, ID model, dan nama berkas dibiarkan apa adanya (verbatim). Nilai privat telah diganti placeholder bentuk `<...>` — isi dengan nilai milik Anda sendiri.

| Dokumen ID | Dokumen Inggris | Deskripsi satu baris |
|---|---|---|
| [README.id.md](README.id.md) | [README.md](../../README.md) | Gambaran umum repositori dan mulai cepat instalasi Armbian modern serta bypass eMMC. |
| [MODERN_ARMBIAN_6X_INSTALL_GUIDE.md](MODERN_ARMBIAN_6X_INSTALL_GUIDE.md) | [MODERN_ARMBIAN_6X_INSTALL_GUIDE.md](../MODERN_ARMBIAN_6X_INSTALL_GUIDE.md) | Panduan lengkap instalasi Armbian modern, pembersihan PPPwn, migrasi eMMC, dan MicroSD sebagai penyimpanan. |
| [SELF_HEALING_BOOT.md](SELF_HEALING_BOOT.md) | [SELF_HEALING_BOOT.md](../SELF_HEALING_BOOT.md) | Tinjauan boot mandiri-pulih: peta SPOF rantai boot dan SOP pembaruan wajib. |
| [STB_B860H_FULL_SETUP_GUIDE.md](STB_B860H_FULL_SETUP_GUIDE.md) | [STB_B860H_FULL_SETUP_GUIDE.md](../STB_B860H_FULL_SETUP_GUIDE.md) | Panduan penyiapan server lengkap box ini dari flashing hingga auto-patch. |
| [SUMMARY_OF_WORK.md](SUMMARY_OF_WORK.md) | [SUMMARY_OF_WORK.md](../SUMMARY_OF_WORK.md) | Ringkasan seluruh investigasi, perbaikan arsitektural, dan insiden pembaruan kernel. |
| [RESEARCH_AND_RECOVERY_GUIDE.md](RESEARCH_AND_RECOVERY_GUIDE.md) | [RESEARCH_AND_RECOVERY_GUIDE.md](../RESEARCH_AND_RECOVERY_GUIDE.md) | Panduan teknis dan runbook pemulihan boot langsung dari MicroSD untuk eMMC mati. |
| [PERMANENT_SD_BOOT_GUIDE.md](PERMANENT_SD_BOOT_GUIDE.md) | [PERMANENT_SD_BOOT_GUIDE.md](../PERMANENT_SD_BOOT_GUIDE.md) | Panduan modifikasi perangkat keras agar BootROM otomatis boot dari kartu SD. |
| [EMMC_BYPASS_RESEARCH.md](EMMC_BYPASS_RESEARCH.md) | [EMMC_BYPASS_RESEARCH.md](../EMMC_BYPASS_RESEARCH.md) | Riset mendalam BootROM, rantai ATF, suntikan sektor, relokasi kernel, dan patch DTB. |
| [armbian_build_preparation.md](armbian_build_preparation.md) | [armbian_build_preparation.md](../armbian_build_preparation.md) | Panduan mulai cepat framework build Armbian dan konfigurasi papan `aml-s9xx-box`. |

Catatan placeholder: `<user>` = nama pengguna operator Anda; `<stb-password>` = kata sandi STB (buat sendiri); `<hotspot-password>` = kata sandi AP darurat; `<STB-LAN-IP>` / `<STB-WIFI-IP>` / `<TAILSCALE-IP>` = alamat IP Anda (contoh `192.168.1.100`); `<your-tailnet>.ts.net` = tailnet Tailscale Anda; `<COM-PORT>` = port serial Anda (mis. COM5 di Windows); `<repo-checkout>` = lokasi checkout repo Anda. Alamat `192.168.50.1/24` dipertahankan apa adanya karena itu default contoh AP perangkat.
