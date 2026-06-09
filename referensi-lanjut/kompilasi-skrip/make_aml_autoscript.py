import struct
import binascii
import time

def make_uboot_script(input_text, output_file):
    # Force unix line endings
    input_text = input_text.replace('\r\n', '\n')
    data = input_text.encode('utf-8') + b'\x00'
    data_size = len(data)
    data_crc = binascii.crc32(data) & 0xffffffff
    
    # Header format:
    # Magic (4), Header CRC (4), Time (4), Size (4), Load (4), Entry (4), Data CRC (4)
    # OS (1), Arch (1), Type (1), Comp (1), Name (32)
    
    magic = 0x27051956
    timestamp = int(time.time())
    load_addr = 0
    entry_addr = 0
    
    os = 0 # Invalid OS (doesn't matter much for script)
    arch = 2 # ARM
    img_type = 6 # Script
    comp = 0 # None
    name = b'Autoscript' + b'\x00' * 22
    
    # Pack with header crc set to 0
    header_no_crc = struct.pack('>I I I I I I I B B B B 32s', 
                                magic, 0, timestamp, data_size, load_addr, entry_addr, data_crc,
                                os, arch, img_type, comp, name)
                                
    # Calculate header CRC
    header_crc = binascii.crc32(header_no_crc) & 0xffffffff
    
    # Pack full header
    header = struct.pack('>I I I I I I I B B B B 32s', 
                         magic, header_crc, timestamp, data_size, load_addr, entry_addr, data_crc,
                         os, arch, img_type, comp, name)
                         
    with open(output_file, 'wb') as f:
        f.write(header)
        f.write(data)
        
if __name__ == '__main__':
    script_content = """echo "Start Armbian Boot Script"
setenv loadaddr 0x44000000
setenv kernel_addr_r 0x11000000
setenv ramdisk_addr_r 0x15000000
setenv fdt_addr_r 0x1000000

echo "Trying u-boot.ext on mmc 0"
fatload mmc 0 0x1000000 u-boot.ext
go 0x1000000

echo "Trying uEnv.txt on mmc 0"
fatload mmc 0 ${loadaddr} uEnv.txt
env import -t ${loadaddr} ${filesize}
setenv bootargs ${APPEND}
fatload mmc 0 ${kernel_addr_r} ${LINUX}
fatload mmc 0 ${ramdisk_addr_r} ${INITRD}
fatload mmc 0 ${fdt_addr_r} ${FDT}
fdt addr ${fdt_addr_r}
booti ${kernel_addr_r} ${ramdisk_addr_r} ${fdt_addr_r}
"""
    # Force LF line endings
    script_content = script_content.replace('\r\n', '\n')
    make_uboot_script(script_content, 'aml_autoscript')

    print("aml_autoscript created successfully!")

