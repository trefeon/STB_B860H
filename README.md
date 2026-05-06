# ZTE B860H Armbian SD Card Boot Guide (Bootloop Fix)

This repository provides a reliable method to boot **Armbian Linux** on the **ZTE B860H V1/V2 (Amlogic S905X - Board p212)** via an SD card. 

This specific guide is designed to bypass the common **"saveenv" bootloop** that occurs when the internal eMMC of the STB is corrupted, locked, or unwritable.

## 🌟 Why this method?

Standard Armbian `aml_autoscript` files attempt to write boot variables to the device's internal storage (`saveenv`). If your eMMC is damaged, this process fails, and the STB loops infinitely into recovery or the boot logo.

By using the scripts provided in this repository, we instruct the STB to **directly chainload** the secondary bootloader (`u-boot.ext`) off the SD card, completely bypassing any writes to the internal memory.

---

## 🚀 Installation Guide

### 1. Flash the SD Card
1. Get a reliable MicroSD Card (minimum 8GB, Class 10).
2. Download the [Armbian Imager](https://github.com/armbian/imager) (Highly Recommended) or use Balena Etcher.
3. Select an Ophub Armbian image for `Amlogic S9xxx` (either `.img.xz` or `.img.gz`).
4. Flash the image to your SD card and wait for completion.

### 2. Configure the BOOT Partition
Once flashing is done, re-insert your SD card so the `BOOT` partition mounts on your PC. You need to make three critical changes:

#### A. Activate the Secondary Bootloader
The B860H's default bootloader needs an extension.
1. Open the `BOOT` partition.
2. Find the file named `u-boot-s905x-s912`.
3. **Rename** it exactly to `u-boot.ext`.

#### B. Set the Device Tree (DTB)
Tell Armbian which hardware it's running on:
1. Open `uEnv.txt` (or `extlinux/extlinux.conf` depending on the image).
2. Locate the `FDT` line.
3. Change it to point to the p212 device tree:
   ```ini
   FDT=/dtb/amlogic/meson-gxl-s905x-p212.dtb
   ```
4. Save the file.

#### C. Apply the Bootloop Bypass (Crucial Step)
If you have eMMC issues, do this to prevent bootloops:
1. In the `BOOT` partition, find `s905_autoscript`.
2. Delete (or rename) the existing `aml_autoscript`.
3. **Copy** `s905_autoscript` and **Rename** the copy to `aml_autoscript`.

*(Alternatively, you can just download the pre-compiled `aml_autoscript` from the `boot-scripts/` folder in this repository and overwrite the one on your SD card).*

### 3. Booting the STB
1. Ensure the STB is powered off.
2. Insert the prepared SD Card.
3. Plug in the power cable.
4. The device will automatically read the `aml_autoscript` from the SD card and boot directly into Armbian Linux!

---

## 🛠️ Repository Contents

*   `boot-scripts/`: Contains the compiled boot bypass scripts (`aml_autoscript` and `s905_autoscript`).
*   `src/`: Contains the original human-readable Ophub script texts and a python compiler (`make_aml_autoscript.py`) if you wish to build the scripts yourself using `mkimage`.
*   `logs/`: Contains reference UART boot logs demonstrating successful bypass of the `saveenv` failure.

---

## 📝 First Login
Once the system boots and connects to your network:
*   **Username:** `root`
*   **Default Password:** `1234`

You will be prompted to change the password immediately upon your first login.
