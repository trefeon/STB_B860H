# B860H deterministic eMMC boot - ALL LITERAL, no variables.
# U-Boot hush pre-expands ${...} inside autoscr scripts, so this script
# deliberately uses zero variables. Regenerate with mkimage if edited:
#   mkimage -A arm -O linux -T script -C none -n 'B860H literal' \
#     -d emmc_autoscript.cmd emmc_autoscript
setenv bootargs root=LABEL=ROOTFS_EMMC rootdelay=5 rootflags=data=writeback rw rootfstype=ext4 console=ttyAML0,115200n8 console=tty0 no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0 max_loop=128 cgroup_enable=cpuset cgroup_memory=1 cgroup_enable=memory swapaccount=1 video=HDMI-A-1:1920x1080@60e plymouth.enable=0
# Updater compat: kernel updater hard-requires an initrd-address declaration (value already correct). Unused at boot, load addresses below stay literal.
setenv initrd_addr 0x15000000
fatload mmc 1:1 0x11000000 /zImage
fatload mmc 1:1 0x15000000 /uInitrd
fatload mmc 1:1 0x1000000 /dtb/amlogic/meson-gxl-s905x-b860h.dtb
booti 0x11000000 0x15000000 0x01000000
# Fallback slot: known-good set from tools/snapshot_boot_good.sh. booti returns only on failure, so reaching here means primary failed.
fatload mmc 1:1 0x11000000 /zImage.good
fatload mmc 1:1 0x15000000 /uInitrd.good
fatload mmc 1:1 0x1000000 /dtb/amlogic/meson-gxl-s905x-b860h.dtb.good
booti 0x11000000 0x15000000 0x01000000
