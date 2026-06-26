import os
import shutil

TARGET_DTB = r"f:\dtb\amlogic\meson-gxl-s905x-p212.dtb"
OFFSET = 28280  # From find_gpio_offset.py
OLD_VAL = b'\x00\x00\x00\x15\x00\x00\x00\x55\x00\x00\x00\x01'
NEW_VAL = b'\x00\x00\x00\x15\x00\x00\x00\x4c\x00\x00\x00\x01'

def patch_dtb(filepath=TARGET_DTB):
    if not os.path.exists(filepath):
        print(f"ERROR: DTB file not found: {filepath}")
        return False
        
    print(f"Target DTB: {filepath}")
    
    # Read to verify bytes at offset
    with open(filepath, 'rb') as f:
        f.seek(OFFSET)
        current_bytes = f.read(12)
        
    if current_bytes == NEW_VAL:
        print("DTB is already patched with the correct reset-gpios value.")
        return True
        
    if current_bytes != OLD_VAL:
        print(f"ERROR: Bytes at offset {OFFSET} do not match expected original value.")
        print(f"Expected: {OLD_VAL.hex()}")
        print(f"Found:    {current_bytes.hex()}")
        return False
        
    # Backup original DTB
    backup_path = filepath + ".bak"
    if not os.path.exists(backup_path):
        print(f"Creating backup of original DTB to: {backup_path}...")
        try:
            shutil.copy2(filepath, backup_path)
            print("Backup created successfully.")
        except Exception as e:
            print(f"ERROR creating backup: {e}")
            return False
    else:
        print(f"Backup already exists: {backup_path}. Skipping backup.")
        
    # Patch the bytes
    print("Patching reset-gpios pin from 85 (0x55) to 76 (0x4c)...")
    try:
        with open(filepath, 'r+b') as f:
            f.seek(OFFSET)
            f.write(NEW_VAL)
            f.flush()
            os.fsync(f.fileno())
        print("Patch applied successfully.")
    except Exception as e:
        print(f"ERROR writing patch to DTB: {e}")
        return False
        
    # Verify patch
    with open(filepath, 'rb') as f:
        f.seek(OFFSET)
        verified_bytes = f.read(12)
        
    if verified_bytes == NEW_VAL:
        print("Verification SUCCESS! DTB patched correctly.")
        return True
    else:
        print(f"Verification FAILED: Expected {NEW_VAL.hex()}, got {verified_bytes.hex()}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Patch DTB pin config to redirect reset-gpios of SDIO Wi-Fi from pin 85 (0x55) to 76 (0x4c).")
    parser.add_argument("dtb_path", nargs="?", default=TARGET_DTB, help="Path to the DTB file (default: f:\\dtb\\amlogic\\meson-gxl-s905x-p212.dtb)")
    
    args = parser.parse_args()
    patch_dtb(args.dtb_path)
