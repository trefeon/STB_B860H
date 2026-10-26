echo "=== BOOTING CLEAN NATIVE ANDROID TV (B860H DTB + EARLYCON) ==="
setenv bootargs "root=/dev/sda2 rootwait rootfstype=ext4 rw init=/init earlycon=meson,0xc81004c0 console=ttyAML0,115200 no_console_suspend androidboot.selinux=permissive logo=osd1,loaded,0x13000000,1080p60hz vout=1080p60hz,enable androidboot.hardware=amlogic androidboot.dtb_idx=0"
load usb 0:1 0x11000000 Image
load usb 0:1 0x15000000 uInitrd
load usb 0:1 0x01000000 dtb.img
booti 0x11000000 0x15000000 0x01000000
