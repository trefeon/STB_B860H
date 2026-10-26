> Terjemahan Bahasa Indonesia dari ../PERMANENT_SD_BOOT_GUIDE.md (English canonical).
> Kembali ke dokumen Inggris: [PERMANENT_SD_BOOT_GUIDE.md](../PERMANENT_SD_BOOT_GUIDE.md)

# Panduan Boot-Otomatis Kartu SD Permanen untuk ZTE B860H V1/V2

Panduan ini menguraikan modifikasi perangkat keras permanen yang diperlukan agar bootloader ZTE B860H V1/V2 memprioritaskan dan melakukan boot dari kartu MicroSD secara otomatis setiap kali daya tersambung, tanpa perlu menahan tombol recovery/daya fisik.

---

## 1. Mengapa Modifikasi Perangkat Keras Diperlukan
Pada perangkat Amlogic S905X dengan eMMC internal yang gagal:
1. **Bacaan Kecepatan Rendah Berhasil**: Sektor boot eMMC internal masih terbaca pada kecepatan sangat rendah (100–400 kHz) oleh BootROM SoC. Akibatnya, BootROM selalu memboot U-Boot vendor dari flash internal lebih dulu.
2. **Bus Kecepatan Tinggi Gagal**: Setelah U-Boot vendor berjalan, ia mencoba menginisialisasi antarmuka eMMC penuh (kecepatan dan lebar lebih tinggi). Kontroler eMMC yang mati/rusak gagal pada tahap ini (`MMC init failed`), menyebabkan U-Boot kembali ke perintah boot bawaan (`run storeboot`), yang mencoba memuat Android, gagal, dan reboot.
3. **Environment Bersifat Read-Only**: Karena eMMC secara fisik tidak responsif terhadap perintah tulis, `saveenv` U-Boot untuk mengubah perintah boot permanen selalu gagal.
4. **Kesimpulan**: Untuk memaksa BootROM SoC melewati eMMC sepenuhnya dan boot langsung dari sektor mentah kartu SD Anda (yang berisi U-Boot hasil patch), Anda harus menonaktifkan sinyal clock (CLK) eMMC secara fisik.

---

## 2. Opsi Mod Perangkat Keras

### Opsi A: Lepas Resistor CLK (Paling Rapi & Disarankan)
Papan Amlogic merutekan sinyal clock dari CPU ke eMMC melalui resistor seri kecil (biasanya 33 ohm, berlabel `CLK` atau terletak tepat di samping eMMC). Melepas resistor ini memutus jalur clock secara fisik, menonaktifkan eMMC.

#### Langkah 1: Buka Casing
- Lepaskan kaki karet pada bagian bawah TV box.
- Lepaskan sekrup di bawah kaki tersebut.
- Gunakan alat congkel plastik untuk membuka pengait plastik casing.
- Lepaskan heatsink bila perlu.

#### Langkah 2: Temukan eMMC dan Resistor CLK
- Temukan chip persegi besar berlabel **Samsung**, **SK Hynix**, **Toshiba**, atau **Sandisk** (inilah eMMC).
- Perhatikan sederet resistor kecil tepat di samping chip eMMC.
- Pada papan **B860H V1/V2** (PCB biru atau hijau), ada resistor berlabel **R87** (sering dipakai sebagai resistor pin recovery pendek) dan sederet resistor tepat di samping pin eMMC.
- Jalur CLK melewati sebuah resistor. Pada banyak revisi B860H V1/V2, resistor CLK terletak dekat eMMC dan dapat dikenali dari label kecil `CLK` yang dicetak pada silk screen, atau dengan menelusuri trace dari pad clock eMMC (pin `W6` pada paket BGA153).
- *Lokasi Umum per Revisi*:
  - **B860H V1 (papan Merah/Biru)**: Resistor CLK biasanya berupa resistor hitam mungil dalam kelompok 4-5 resistor tepat di samping tepi chip eMMC.
  - **B860H V2 (papan Biru/Hijau)**: Letaknya dekat sudut heatsink CPU.

#### Langkah 3: Lepas Resistor
- Dengan solder berujung halus atau stasiun rework udara panas, desolder dan lepaskan resistor CLK dari papan.
- Alternatifnya, Anda dapat memakai pisau hobi/skalpel halus untuk menggores tipis trace tembaga CLK pada PCB yang menuju resistor. (Ini irreversibel kecuali Anda menyolder kabel jumper kemudian, sehingga melepas resistor tetap lebih disarankan).

---

### Opsi B: Solder CLK ke GND (Metode Kabel Jumper)
Bila Anda tidak ingin melepas resistor, Anda dapat menyolder kabel jumper tipis untuk meng-ground-kan sinyal CLK. Ini menjepit sinyal clock ke 0V, membuat eMMC tak terlihat oleh BootROM.

1. Temukan titik uji CLK atau sisi resistor CLK yang paling dekat dengan chip eMMC.
2. Solder kabel tembaga berinsulasi tipis (kabel enamel jumper) dari titik CLK.
3. Solder ujung lain kabel ke titik Ground (GND) pada papan. (Casing logam luar port USB, port HDMI, atau slot microSD adalah titik ground yang bagus).
4. Amankan kabel dengan setetes kecil lem panas atau kapton tape agar tidak menyentuh komponen lain.

---

## 3. Perilaku Boot Pasca-Mod
Setelah jalur CLK dinonaktifkan:
1. **Daya Tersambung**: BootROM SoC menyala dan mencoba membaca eMMC.
2. **Timeout Seketika**: Karena sinyal clock hilang, eMMC tidak merespons. BootROM langsung timeout (~10ms).
3. **Failover Kartu SD**: BootROM berpindah ke `mmc0` (slot MicroSD).
4. **Bootloader Termuat**: BootROM membaca Sektor 0/1 kartu SD, mendeteksi tanda `uboot_HG680P-sdboot.bin` yang disuntikkan, memuatnya ke DRAM, lalu boot.
5. **Boot-Otomatis Armbian**: U-Boot kartu SD berjalan, membaca `aml_autoscript` kustom dari partisi BOOT kartu SD, dan langsung memboot Linux Armbian!

Tanpa tombol, konsol serial, atau keyboard. TV box berperilaku persis seperti komputer papan tunggal standar (seperti Raspberry Pi), boot langsung dari kartu SD.
