import os
import shutil
import struct

TARGET_DTB = r"f:\dtb\amlogic\meson-gxl-s905x-p212.dtb"
OLD_VAL = b'\x00\x00\x00\x15\x00\x00\x00\x55\x00\x00\x00\x01'
NEW_VAL = b'\x00\x00\x00\x15\x00\x00\x00\x4c\x00\x00\x00\x01'

def find_reset_gpios_offset(filepath):
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        if len(data) < 40:
            return None
        magic, totalsize, off_dt_struct, off_dt_strings, off_mem_rsvmap, version, last_comp_version, boot_cpuid_phys, size_dt_strings, size_dt_struct = struct.unpack('>IIIIIIIIII', data[:40])
        strings_data = data[off_dt_strings:off_dt_strings+size_dt_strings]
        struct_data = data[off_dt_struct:off_dt_struct+size_dt_struct]
        
        idx = 0
        node_stack = []
        while idx < len(struct_data):
            token = struct.unpack('>I', struct_data[idx:idx+4])[0]
            idx += 4
            if token == 1: # FDT_BEGIN_NODE
                name_bytes = []
                while struct_data[idx] != 0:
                    name_bytes.append(struct_data[idx])
                    idx += 1
                idx += 1
                idx = (idx + 3) & ~3
                node_name = bytes(name_bytes).decode('ascii', errors='ignore')
                node_stack.append(node_name)
            elif token == 2: # FDT_END_NODE
                if node_stack:
                    node_stack.pop()
            elif token == 3: # FDT_PROP
                val_len, name_off = struct.unpack('>II', struct_data[idx:idx+8])
                p_end = strings_data.find(b'\x00', name_off)
                prop_name = strings_data[name_off:p_end].decode('ascii', errors='ignore')
                current_path = "/" + "/".join(node_stack)
                if current_path == "//sdio-pwrseq" and prop_name == "reset-gpios":
                    return off_dt_struct + idx + 8
                idx += 8 + val_len
                idx = (idx + 3) & ~3
            elif token == 4: # FDT_NOP
                pass
            elif token == 9: # FDT_END
                break
    except Exception as e:
        print(f"Error parsing DTB: {e}")
    return None

def patch_dtb(filepath=TARGET_DTB):
    if not os.path.exists(filepath):
        print(f"ERROR: DTB file not found: {filepath}")
        return False
        
    print(f"Target DTB: {filepath}")
    
    offset = find_reset_gpios_offset(filepath)
    if offset is None:
        print("ERROR: Could not dynamically locate reset-gpios offset in DTB.")
        return False
        
    print(f"Found reset-gpios offset dynamically at: {offset} (0x{offset:x})")
    
    # Read to verify bytes at offset
    with open(filepath, 'rb') as f:
        f.seek(offset)
        current_bytes = f.read(12)

        
    if current_bytes == NEW_VAL:
        print("DTB is already patched with the correct reset-gpios value.")
        return True
        
    if current_bytes != OLD_VAL:
        print(f"ERROR: Bytes at offset {offset} do not match expected original value.")
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
            f.seek(offset)
            f.write(NEW_VAL)
            f.flush()
            os.fsync(f.fileno())
        print("Patch applied successfully.")
    except Exception as e:
        print(f"ERROR writing patch to DTB: {e}")
        return False
        
    # Verify patch
    with open(filepath, 'rb') as f:
        f.seek(offset)
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
    parser.add_argument("dtb_path", nargs="?", default=None, help="Path to the DTB file to patch in place (required)")

    args = parser.parse_args()
    if not args.dtb_path:
        parser.error("dtb_path is required")
    patch_dtb(args.dtb_path)
