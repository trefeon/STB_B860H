# B860H Full Setup Guide: Armbian Server with MicroSD as Internal Storage

Board: **ZTE ZXV10 B860H V1/V2 (Amlogic S905X, 2 GB RAM, 8 GB eMMC)**.
OS: **Armbian 26.11.0 Bookworm, kernel 6.12.112-ophub (mainline LTS)**.
Role: headless home server. The MicroSD card is **not** a boot medium — it is
permanent internal storage (data, swap, bound homes).

This guide reproduces the exact working setup on this box, from flashing to
auto-patching. Companion automation lives in `tools/`; diagnostics in
`tools/diagnostics/`.

---

## 0. Architecture at a glance

```text
eMMC 7.3 GB (/dev/mmcblk2)
├── p1 511 MB  vfat   BOOT_EMMC      /boot     (kernel, initrd, DTB, autoscripts)
└── p2 6.1 GB  ext4   ROOTFS_EMMC    /         (system, 3.3 GB free)

MicroSD 32 GB (/dev/mmcblk1, single partition, ext4, LABEL=SD_STORAGE)
└── p1 29.7 GB  ext4  SD_STORAGE     /mnt/storage
    ├── swapfile            (4 GB swap, prio -2)
    ├── `home_<user>/`  --> bind-mounted to `/home/<user>`
    ├── opt/          --> bind-mounted to /opt
    └── docker/           (DockerRootDir)
```

Network: `eth0` `<STB-LAN-IP>` (primary, metric 100) · `wlan0` `<STB-WIFI-IP>`
(STA fallback, metric 600) · Tailscale `<TAILSCALE-IP>` · Hotspot `B860H-AP`
(`wlan1`, `192.168.50.1`/24 AP default, emergency use only — see §8).

SSH aliases on the operator laptop: `ssh stb` ( eth), `ssh stb-wifi`,
`ssh stb-ts`.

---

## 1. Prerequisites

- Installer MicroSD ≥ 16 GB (any spare card; kept separate from the storage card below) + card reader.
- **Storage MicroSD ≥ 16 GB, A1-rated or better** (this box: 32 GB). Card quality
  decides the server's life: random I/O on cheap cards stalls the whole box.
  Prefer endurance/A1 cards; never use the card that came free with a gadget.
- USB TTL adapter (CH340) wired to header `X2`: Gnd→GND, Tx→RXD, Rx→TXD.
  **Do not connect VCC** (box is 12 V powered).
- Serial settings: **115200 8N1**, observed as `<COM-PORT>` (e.g. `COM5` on Windows).

---

## 2. Get the Armbian image (source + best practice)

Upstream source: **Ophub `amlogic-s9xxx-armbian` GitHub releases**
(`github.com/ophub/amlogic-s9xxx-armbian/releases`). Pick the file matching
all four markers: **`amlogic_s905x-b860h`** (board) + **`bookworm`**
(Debian 12) + **`server`** (no desktop) + **`6.12`** (mainline LTS kernel).
This box runs:
`Armbian_26.11.0_amlogic_s905x-b860h_bookworm_6.12.112_server_2026.10.15.img.gz`.

Best practice before flashing — verify, then write:
```bash
bash tools/download_image.sh          # curl + gunzip -> ./Armbian_b860h.img (or pass a dest dir)
# script auto-verifies sha256 when upstream publishes a .sha256 file
python tools/flash_sd.py             # Run as Administrator (Win32 raw write)
```
Alternatives: BalenaEtcher / Rufus with the same `.img`.
Always keep the installer card intact until the eMMC system is proven
booting (it is your recovery medium).

---

## 3. First boot and migrate to eMMC

1. Insert MicroSD, power on, log in over SSH (`root` / `1234`).
2. Run the installer and pick the B860H profile:
   ```bash
   sudo armbian-install        # box ID 106 (B860H), filesystem ext4 (1)
   ```
   This installs the system to internal eMMC (`BOOT_EMMC` + `ROOTFS_EMMC`).
3. `sudo poweroff`, remove the card, power on — the box now runs from eMMC.

Critical boot file on eMMC `/boot/uEnv.txt`:

```ini
LINUX=/zImage
INITRD=/uInitrd
FDT=/dtb/amlogic/meson-gxl-s905x-b860h.dtb
APPEND=root=LABEL=ROOTFS_EMMC rootdelay=5 rootflags=data=writeback rw rootfstype=ext4 console=ttyAML0,115200n8 console=tty0 no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0 max_loop=128 cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory swapaccount=1 video=HDMI-A-1:1920x1080@60e plymouth.enable=0
```

---

## 4. Repurpose MicroSD as internal storage

Wipe the card to **one raw ext4 partition** (no bootloader, no FAT — otherwise
Amlogic BootROM prioritizes it over eMMC), label it, and wire it in:

1. On any Linux box (or the STB itself booted from eMMC *without* the card):
   partition the whole card as a single Linux partition, `mkfs.ext4 -L SD_STORAGE`.
   (Amlogic USB Burning Tool leftovers or x86 bootstrap bytes in sector 0
   crash the BootROM — zero bytes 0–445 if the card was partitioned by
   Windows tools: `dd if=/dev/zero of=/dev/sdX bs=1 count=446 conv=notrunc`.)
2. Add to `/etc/fstab` (all SD-backed mounts use `nofail` so the box still
   boots with the card removed):

```fstab
LABEL=BOOT_EMMC       /boot        vfat    defaults 0 2
LABEL=ROOTFS_EMMC     /            ext4    defaults,noatime,nodiratime,commit=600,errors=remount-ro 0 1
tmpfs                 /tmp         tmpfs   defaults,nosuid 0 0
/mnt/storage/swapfile none        swap    sw,nofail 0 0
LABEL=SD_STORAGE      /mnt/storage ext4    defaults,noatime,nodiratime,nofail 0 2
/mnt/storage/home_<user> /home/<user> none defaults,bind,nofail 0 0
/mnt/storage/opt /opt none        defaults,bind,nofail 0 0
```

3. Create the backing dirs and swapfile on the card:
   ```bash
   sudo mkdir -p /mnt/storage/{home_<user>,opt,docker,data}
   sudo dd if=/dev/zero of=/mnt/storage/swapfile bs=1M count=4096
   sudo chmod 600 /mnt/storage/swapfile && sudo mkswap /mnt/storage/swapfile
   sudo mount -a && sudo swapon -a
   ```
   Result: ~22 GB free on `/mnt/storage`, 4 GB swapfile (prio -2) under
   1.8 GB zram (prio 100).
   SD-as-internal best practice (why it is built this way):
   - One partition, no bootloader/FAT: BootROM always probes the slot first;
     anything bootable-looking there hijacks the boot. `nofail` everywhere so
     a dead/removed card never blocks booting.
   - `noatime,nodiratime,commit=600` + capped journals: cuts SD write
     amplification dramatically; the card mostly sees sequential media writes.
   - Swap on SD is last resort only (prio -2 under zram prio 100): with
     1.8 GB RAM + zram, the SD swapfile almost never gets touched, so wear
     is negligible — but it saves the box from the OOM killer on spikes.
   - SD cards have no TRIM: never `fstrim` the card (weekly `fstrim.timer`
     only benefits eMMC); when the card ages, replace it — system and data
     are separable by design (`/home`, `/opt`, `/mnt/storage`, Docker).


---

## 5. Auto-patch: Wi-Fi driver and DTB Bluetooth fix

Stock Ophub images ship without the out-of-tree RTL8189FS driver and with a
phantom Broadcom-BT node that hangs boot 15 s. One command from the laptop,
no STB-side compile needed:

```bash
bash tools/ship_patch.sh stb
```

What it does (`tools/auto_patch_wifi_bt.sh` + `packages/b860h_patch/`):
- Installs prebuilt `8189fs.ko` (3.05 MB) for kernel 6.12.112.
- Installs `meson-gxl-s905x-b860h.dtb` (40.8 KB) with the phantom BT node disabled.
- Wi-Fi comes up in < 2 s with no internet traffic.

---

## 6. Deterministic boot (fix for the `gxl_p212_v1#` prompt)

Vendor U-Boot (`bootcmd=run storeboot`) has **no hook** for eMMC boot scripts:
on a cold boot it tries the (deleted) Android partition, scans SD/USB for
recovery, then stops at the `gxl_p212_v1#` prompt. Fix applied on this box:

1. `/boot/emmc_autoscript` + `/boot/aml_autoscript` — deterministic scripts,
   compiled **on the STB** with `mkimage` (never on Windows: CRLF and
   shell-mangled `${...}` break them). Content is fully literal (no U-Boot
   variables at all — this U-Boot pre-expands `${...}` inside `autoscr`
   scripts, which silently empties them):
   ```text
   setenv bootargs root=LABEL=ROOTFS_EMMC ... (full APPEND line, literal)
   fatload mmc 1:1 0x11000000 /zImage
   fatload mmc 1:1 0x15000000 /uInitrd
   fatload mmc 1:1 0x1000000 /dtb/amlogic/meson-gxl-s905x-b860h.dtb
   booti 0x11000000 0x15000000 0x01000000
   ```
   Sources live in this repo at `boot/emmc_autoscript.cmd`
   (byte-identical copy used for both files).
2. NVRAM now boots straight into it (one-time, UART-verified):
   ```text
   setenv bootcmd 'fatload mmc 1:1 0x01020000 emmc_autoscript; autoscr 0x01020000'
   saveenv   # Writing to MMC(1)... done
   ```

Recovery if boot ever drops to the prompt: interrupt autoboot (space key),
run the five lines above manually, then inspect.

---

## 7. HDMI console policy (headless-light by default)

`tools/hdmi-console.sh` + udev rule `tools/99-hdmi-console.rules`,
installed at `/usr/local/bin/hdmi-console.sh` and
`/etc/udev/rules.d/99-hdmi-console.rules`, plus oneshot unit
`hdmi-console-boot.service` so the policy also applies at boot.

- HDMI plugged (EDID present) → unblank framebuffer, `getty@tty1` runs.
- HDMI unplugged (EDID empty) → blank output, `getty@tty1` stopped.
- NOTE: the meson driver always reports `status=connected` (the `video=...e`
  flag forces the connector on), so presence is detected via EDID, not status.

---

## 8. Hotspot and emergency failover

- Profile `B860H-AP` (SSID `B860H-AP`, WPA2, 192.168.50.1/24 on `wlan1`).
  STA (`wlan0`, home Wi-Fi) and AP run concurrently on the single RTL8189FS
  radio — verified working.
- Default state: hotspot **off** (`autoconf=no`). Emergency coverage is
  automatic: `tools/hotspot-failover.sh` (every 1 min via
  `hotspot-failover.{service,timer}`) brings the AP up after two consecutive
  failed uplink pings and takes it down when the uplink returns.
- Emergency SSH while the LAN is down: join `B860H-AP` (password
  `<hotspot-password>` — set your own on first boot), then
  `ssh <user>@192.168.50.1` (the AP default gateway; example address).
  Change the password with:
  `nmcli con mod B860H-AP wifi-sec.psk <new-password>`.

---

## 9. Server baseline and applied optimizations

- SSH (key auth), Docker (root dir on SD), Tailscale, swap+zram, log2ram-style
  ramlog, journal capped at 50 MB, rsyslog removed, BBR + fq, `schedutil`
  governor, SD scheduler `none` (udev-persistent), eMMC `mq-deadline`,
  swappiness 100 (correct with zram as primary swap), Bluetooth stack masked
  (no BT hardware on this board).
- Applied via `tools/optimizations/apply_optimizations.sh`;
  host-specific deltas live in `/etc/sysctl.d/99-server-opt.conf`,
  `/etc/udev/rules.d/60-iosched.rules`, `/etc/systemd/journald.conf.d/`.

---

## 10. Verification matrix (all passing on this box)

| Test | Result |
|---|---|
| Soft reboot (`sudo reboot`) | Hands-off to login, 0 failed services |
| Cold boot (unplug → replug power) | Hands-off to login, with and without HDMI |
| HDMI plugged | Login prompt on TV |
| HDMI unplugged | Blank output, getty stopped, ~300 MB RAM used |
| Wi-Fi STA + AP concurrently | STA associated (rssi 80%+) while AP beacons |
| Hotspot failover | AP up after uplink loss, down on recovery (tested with ICMP block) |
| Docker | `hello-world` runs (ARM image) |
| eMMC health | 2.7/6.0 GB used; no stale kernels; fstrim timer active |

Monitor any boot live from the laptop:
```bash
python tools/diagnostics/boot_monitor.py --dir logs
```
It auto-detects each reboot, timestamps every line, and closes each boot log
with a verdict (`OK login t+...`, `STOPPED at U-Boot prompt`, `STUCK ...`).

---

## 11. Maintenance notes

- **Never edit `/boot/*.cmd` on Windows** — compile on the STB with `mkimage`
  (`cat -A` the file first: lines must end `$`, never `^M$`).
- **Never send U-Boot `${...}` through string-based SSH tools** — they can be
  eaten before reaching U-Boot. Use literal commands or a serial session
  (`tools/diagnostics/uboot_interactive.py`, `auto_restore_linux.py`).
- Keep the SD card as one ext4 partition; never put a bootloader on it.
- `packages/b860h_patch/` is the offline patch bundle; `tools/ship_patch.sh`
  deploys it. `tools/vendor/` holds the opaque Amlogic `ampack.exe`.
- Full repo conventions: bash+ssh for STB commands, Python only for
  serial-UART, binary parsing, or Windows raw-disk I/O.
- Kernel update SOP (`armbian-update -k <ver> -u stable`): updater needs
  `setenv initrd_addr 0x15000000` in `/boot/emmc_autoscript.cmd` (present
  since 2026-10-26); on reinstall use `-b no` (backup already in `/ddbr`);
  after every update re-patch DTB + rebuild `8189fs` (`tools/ship_patch.sh`
  flow), then reboot and verify `wlan0`. Details: `SUMMARY_OF_WORK.md` §8.
