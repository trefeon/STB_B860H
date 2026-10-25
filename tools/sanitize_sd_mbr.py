import struct
import sys

backup_file = "D:/mbr_backup.bin"
log_file = "D:/sanitize_mbr_log.txt"

with open(log_file, "w") as log:
    try:
        # Open physical drive for read/write
        with open(r"\\.\PhysicalDrive2", "r+b") as f:
            mbr = bytearray(f.read(512))
            
            # Save backup
            with open(backup_file, "wb") as bf:
                bf.write(mbr)
            log.write(f"MBR backed up to {backup_file}\n")
            log.write(f"Original first 16 bytes: {mbr[:16].hex()}\n")
            log.write(f"Partition 1 status: {hex(mbr[446])}, type: {hex(mbr[450])}\n")
            log.write(f"Signature: {hex(mbr[510])} {hex(mbr[511])}\n")
            
            # Zero out bootstrap code (bytes 0 to 445)
            # This ensures Amlogic BootROM never tries to execute x86 PC-DOS bootstrap code
            for i in range(446):
                mbr[i] = 0x00
            
            # Ensure partition 1 is NOT marked active/bootable (status should be 0x00)
            mbr[446] = 0x00
            
            # Write back sanitized MBR
            f.seek(0)
            f.write(mbr)
            f.flush()
            
            log.write("Successfully sanitized sector 0 bootstrap area (bytes 0-445 zeroed).\n")
            log.write(f"New first 16 bytes: {mbr[:16].hex()}\n")
            log.write("Partition table and 0x55AA signature preserved intact.\n")
    except Exception as e:
        log.write(f"ERROR: {e}\n")

print("Sanitization script finished.")
