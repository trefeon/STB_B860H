import struct
import os
import sys

def find_reset_gpios_offset(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
        
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
                # Absolute offset in file:
                # 1. off_dt_struct is the start of the struct block
                # 2. idx is the start of val_len, name_off (which is 8 bytes)
                # 3. idx + 8 is the start of the value data
                absolute_offset = off_dt_struct + idx + 8
                val_data = struct_data[idx+8:idx+8+val_len]
                print(f"Found reset-gpios in {current_path}:")
                print(f"  Absolute file offset: {absolute_offset} (0x{absolute_offset:x})")
                print(f"  Length: {val_len} bytes")
                print(f"  Value (hex): {val_data.hex()}")
                u32s = struct.unpack(f'>{val_len//4}I', val_data)
                print(f"  Value (parsed): {list(u32s)}")
                return absolute_offset
                
            idx += 8 + val_len
            idx = (idx + 3) & ~3
            
        elif token == 4: # FDT_NOP
            pass
        elif token == 9: # FDT_END
            break
            
    print("Could not find reset-gpios property for sdio-pwrseq")
    return None

if len(sys.argv) < 2:
    sys.exit(f"Usage: {sys.argv[0]} <dtb-file>")
find_reset_gpios_offset(sys.argv[1])
