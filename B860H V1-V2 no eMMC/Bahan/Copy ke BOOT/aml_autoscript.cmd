mmc dev 0
mmc rescan

fatload mmc 0:1 0x1000000 uEnv.txt
env import -t 0x1000000 ${filesize}

setenv bootargs ${APPEND}

fatload mmc 0:1 0x11000000 ${LINUX}
fatload mmc 0:1 0x15000000 ${INITRD}
fatload mmc 0:1 0x1000000 ${FDT}

fdt addr 0x1000000

booti 0x11000000 0x15000000 0x1000000
