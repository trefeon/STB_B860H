import struct
import os
import shutil

TARGET_FILE = r"f:\Image"
TARGET_OFFSET = 0x1080000

def patch_kernel_header(filepath, new_offset):
    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return False
        
    print(f"Target Kernel Image: {filepath}")
    
    # 1. Read existing header
    with open(filepath, 'rb') as f:
        header = f.read(64)
        
    if len(header) < 64:
        print("ERROR: File too small to contain a valid ARM64 Image header.")
        return False
        
    code0, code1, text_offset, image_size, flags, res2, res3, res4, magic, res5 = struct.unpack('<IIQQQQQQII', header)
    
    if magic != 0x644d5241:
        print(f"ERROR: Invalid Magic 0x{magic:08x} (expected 0x644d5241 / 'ARM\\x64')")
        return False
        
    print("Current Header values:")
    print(f"  Magic:       0x{magic:08x} (ARM64)")
    print(f"  Text Offset: 0x{text_offset:x}")
    print(f"  Image Size:  0x{image_size:x} ({image_size} bytes)")
    
    if text_offset == new_offset:
        print(f"Header already has Text Offset set to 0x{new_offset:x}. No changes needed.")
        return True
        
    # 2. Make backup
    backup_path = filepath + ".bak"
    if not os.path.exists(backup_path):
        print(f"Creating backup of original Image to: {backup_path}...")
        try:
            shutil.copy2(filepath, backup_path)
            print("Backup created successfully.")
        except Exception as e:
            print(f"ERROR creating backup: {e}")
            return False
    else:
        print(f"Backup file already exists: {backup_path}. Skipping backup.")
        
    # 3. Patch the file in-place
    print(f"Patching Text Offset to 0x{new_offset:x}...")
    try:
        with open(filepath, 'r+b') as f:
            # text_offset is at offset 8 (bytes 8-15)
            f.seek(8)
            f.write(struct.pack('<Q', new_offset))
            f.flush()
            os.fsync(f.fileno())
        print("Patch applied successfully.")
    except Exception as e:
        print(f"ERROR writing patch to file: {e}")
        return False
        
    # 4. Verify the patched header
    with open(filepath, 'rb') as f:
        patched_header = f.read(64)
        
    p_code0, p_code1, p_text_offset, p_image_size, p_flags, p_res2, p_res3, p_res4, p_magic, p_res5 = struct.unpack('<IIQQQQQQII', patched_header)
    
    print("Verifying Patched Header values:")
    print(f"  Magic:       0x{p_magic:08x}")
    print(f"  Text Offset: 0x{p_text_offset:x}")
    print(f"  Image Size:  0x{p_image_size:x} ({p_image_size} bytes)")
    
    if p_text_offset == new_offset:
        print("Verification SUCCESS! The kernel Image has been patched correctly.")
        return True
    else:
        print(f"Verification FAILED: Expected 0x{new_offset:x}, got 0x{p_text_offset:x}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Patch ARM64 kernel Image text_offset to bypass Secure Monitor / TrustZone crash.")
    parser.add_argument("image_path", nargs="?", default=TARGET_FILE, help="Path to the kernel 'Image' file (default: f:\\Image)")
    parser.add_argument("--offset", type=lambda x: int(x, 0), default=TARGET_OFFSET, help="New text_offset value (default: 0x1080000 / 16.5 MB)")
    
    args = parser.parse_args()
    patch_kernel_header(args.image_path, args.offset)
