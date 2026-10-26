> Terjemahan Bahasa Indonesia dari ../armbian_build_preparation.md (English canonical).
> Kembali ke dokumen Inggris: [armbian_build_preparation.md](../armbian_build_preparation.md)

# Panduan Mulai Cepat Framework Build Armbian

## Kebutuhan
* Mesin x86_64 / aarch64 / riscv64
* RAM minimal 8GB (lebih kecil untuk build non-BTF) dan ruang disk ~50GB untuk instalasi VM, container, atau bare-metal
* **Armbian / Ubuntu Noble 24.04.x** untuk build bawaan atau Linux apa pun berkemampuan Docker untuk container
* **Windows 10/11 dengan subsistem WSL2** yang menjalankan Armbian / Ubuntu Noble 24.04.x
* Hak superuser (sudo terkonfigurasi atau akses root).
* Pastikan sistem Anda mutakhir! Biner Docker yang kedaluwarsa, misalnya, dapat menimbulkan masalah

## Klon repositori
```bash
git clone https://github.com/armbian/build
cd build
```

> **Catatan**:
> * Pastikan path penuh ke skrip build **tidak mengandung spasi**
> * Untuk cabang stabil gunakan rilis titik terakhir `--branch=v24.11`

## Interaktif
Jalankan framework:
```bash
./compile.sh
```

## CLI
```bash
./compile.sh [command] [switch...] [config...]
```

> **Troubleshooting: galat 'unknown terminal type'**
> Saat menjalankan skrip, terutama dari emulator terminal modern (seperti Ghostty, Kitty, WezTerm), Anda bisa menemui galat seperti `'xterm-ghostty': unknown terminal type`
> **Solusi cepat:** Anda dapat memaksa tipe terminal yang lebih umum sebelum menjalankan skrip:
> ```bash
> env TERM=xterm-256color ./compile.sh
> ```

Hanya satu command yang dapat dispesifikasi.

Switch adalah pengaturan parameter yang dipakai oleh framework build itu sendiri (mis. `DEBUG=yes`) atau oleh command tertentu.

Berkas config adalah skrip shell bash yang di-source sesuai urutan spesifikasinya. Berkas ini terutama dipakai untuk mengatur switch tetapi juga dapat mengatur fungsi hook. Berkas harus berada pada direktori `userpatches` dan bernama `config-${arg}.conf` atau `config-${arg}.conf.sh` (`${arg}` adalah argumen dari baris perintah): salah satu, bukan keduanya.

Switch yang diatur pada baris perintah mengalahkan pengaturan dari berkas config, apa pun urutan kemunculannya pada baris perintah.

Contoh:
```bash
./compile.sh build \
BOARD=uefi-x86 \
BRANCH=current \
BUILD_DESKTOP=yes \
BUILD_MINIMAL=no \
DESKTOP_APPGROUPS_SELECTED='browsers chat desktop_tools' \
DESKTOP_ENVIRONMENT=gnome \
DESKTOP_ENVIRONMENT_CONFIG_NAME=config_base \
KERNEL_CONFIGURE=no \
RELEASE=noble
```

Atau, memakai berkas config `userpatches/config-myboard.conf` yang mengatur semua switch ini:
```bash
./compile.sh build \
myboard
```

## Logging
Log ditulis ke `output/logs`. Log lama (semua kecuali build saat ini) dikompresi dan dipindahkan ke `output/logs/archive`.

Format log adalah:
* ANSI - teks dengan escape ANSI untuk pewarnaan - `*.log.ans`
* ASCII (bila ansi2txt tersedia) - teks tanpa escape pewarnaan - `*.log`
* Ringkasan Markdown - `*.md`
* Mentah (bila `RAW_LOG=yes`) - tar berisi semua log mentah - `*.raw.tar`

Untuk log yang jauh lebih verbose atur switch `DEBUG=yes`.

## GitHub Actions
Bila Anda tidak memiliki peralatan yang tepat untuk membangun image sendiri, Anda dapat memakai GitHub Action kami.

### Contoh workflow minimal
Buat `.github/workflows/build.yml` pada repositori Anda:

```yaml
name: Build Armbian Image
on:
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest # ubuntu-24.04-arm, ubuntu-24.04-riscv
    steps:
      - uses: armbian/build@main
        with:
          armbian_token: ${{ secrets.GITHUB_TOKEN }}
          armbian_board: "uefi-x86" # orangepi5 bananapif3
          armbian_release: "noble" # trixie
          armbian_target: "build" # kernel
          armbian_ui: "minimal" # server xfce
          armbian_runner_clean: "yes" # disarankan untuk runner Github
```
Action akan membangun image, membuat GitHub Release pada repositori Anda dan mengunggah artefak.

### Referensi input
| Input | Wajib | Bawaan | Deskripsi |
|---|---|---|---|
| `armbian_token` | **ya** | — | Token akses GitHub (`GITHUB_TOKEN` atau PAT) |
| `armbian_board` | tidak | `uefi-x86` | Platform perangkat keras (mis. `orangepi5`, `rock-5b`) |
| `armbian_target` | tidak | `kernel` | Target build: `kernel` atau `build` (image penuh) |
| `armbian_branch` | tidak | `main` | Cabang framework Armbian |
| `armbian_kernel_branch` | tidak | `current` | Cabang kernel: `current`, `edge`, dll. |
| `armbian_release` | tidak | `noble` | Userspace (mis. `noble`, `bookworm`, `trixie`) |
| `armbian_ui` | tidak | `minimal` | `minimal`, `server`, atau nama lingkungan desktop (mis. `xfce`, `gnome`) |
| `armbian_version` | tidak | *otomatis* | Timpa versi; level patch dinaikkan otomatis dari `stable.json` bila tidak diatur |
| `armbian_compress` | tidak | `sha,img,xz` | Metode kompresi output |
| `armbian_extensions` | tidak | — | Daftar ekstensi build yang dipisahkan koma untuk diaktifkan |
| `armbian_pgp_key` | tidak | — | Kunci GPG privat untuk penandatanganan image (simpan sebagai secret) |
| `armbian_pgp_password` | tidak | — | Frasa sandi GPG (simpan sebagai secret) |
| `armbian_release_title` | tidak | `Armbian image` | Judul GitHub Release |
| `armbian_release_body` | tidak | *(tautan ke perkakas build)* | Isi GitHub Release |
| `armbian_release_tag` | tidak | *otomatis* | Tag GitHub Release; bawaan ke versi terhitung |
| `armbian_artifacts` | tidak | `build/output/images/` | Path artefak untuk diunggah |
| `armbian_runner_clean` | tidak | — | Atur ke nilai non-kosong untuk membebaskan ruang disk pada runner Github-hosted |

### Kustomisasi
Bila repositori Anda memuat direktori `userpatches/`, ia otomatis digabungkan ke framework build. Ini memungkinkan Anda menambah config kernel, patch, atau berkas overlay kustom tanpa melakukan fork pada repositori build utama.

## Konfigurasi Papan Berbasis TVBox S9xx Amlogic (`aml-s9xx-box`)

Berikut konfigurasi papan referensi untuk `aml-s9xx-box` (TVBox berbasis Amlogic S9xx), diambil dari repositori Armbian:

```bash
# Amlogic S9xx based TVBox
BOARD_NAME="aml-s9xx-box"
BOARDFAMILY="meson-gxl"
BOARD_VENDOR="amlogic"
BOARD_MAINTAINER="SteeManMI"
INTRODUCED="2016"
BOOTSIZE="512"
BOOTFS_TYPE="fat"
KERNEL_TARGET="current,edge"
KERNEL_TEST_TARGET="current"
SERIALCON="ttyAML0"
FULL_DESKTOP="yes"
ASOUND_STATE="asound.state.mesongx"
BOOT_FDT_FILE="amlogic/meson-gxl-s905x-p212.dtb"
BOOT_LOGO="desktop"
SRC_EXTLINUX="yes"
SRC_CMDLINE='rootflags=data=writeback console=ttyAML0,115200n8 console=tty0'

function post_family_config__uboot_aml-s9xx-box() {
	# This board type relies on the vendor installed u-boot on emmc to boot
	display_alert "$BOARD" "Configuring ($BOARD) non-u-boot" "info"
	unset BOOTSOURCE
	declare -g BOOTCONFIG='none'
}

function post_family_tweaks_bsp__config_aml-s9xx-box_bsp() {
	: "${destination:?destination is not set}"

	# Important: this board has board-specific bsp-cli files in config/optional/boards/aml-s9xx-box/_packages/bsp-cli
	#            that path is hashed by the bsp-cli hashing function automatically
	display_alert "${BOARD}" "Adjusting perms of bsp-cli files for ${BOARD} in /root" "info"
	run_host_command_logged chmod -v 744 "${destination}"/root/install-aml.sh
	run_host_command_logged chmod -v 6
}
```
