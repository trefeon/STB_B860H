import struct
import os

def parse_dtb(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return None
        
    with open(filepath, 'rb') as f:
        data = f.read()
        
    if len(data) < 40:
        print(f"File too small to be a DTB: {filepath}")
        return None
        
    magic, totalsize, off_dt_struct, off_dt_strings, off_mem_rsvmap, version, last_comp_version, boot_cpuid_phys, size_dt_strings, size_dt_struct = struct.unpack('>IIIIIIIIII', data[:40])
    
    if magic != 0xd00dfeed:
        print(f"ERROR: Invalid DTB Magic 0x{magic:08x} (expected 0xd00dfeed)")
        return None
        
    print(f"DTB File: {filepath}")
    print(f"  Total Size: {totalsize} bytes (File size: {len(data)})")
    print(f"  Format Version: {version} (compatible with {last_comp_version})")
    
    # Extract the strings block
    strings_data = data[off_dt_strings:off_dt_strings+size_dt_strings]
    
    # Let's extract some printable strings from the strings block
    strings = []
    current = []
    for b in strings_data:
        if b == 0:
            if current:
                try:
                    strings.append(bytes(current).decode('ascii', errors='ignore'))
                except:
                    pass
                current = []
        else:
            current.append(b)
            
    print(f"  Number of unique property names (strings): {len(strings)}")
    
    # Let's also print any string properties in the structure block to find "model" and "compatible"
    # The structure block contains tokens:
    # FDT_BEGIN_NODE (0x00000001)
    # FDT_END_NODE (0x00000002)
    # FDT_PROP (0x00000003): has length (4 bytes) and name offset (4 bytes), followed by value aligned to 4 bytes
    # FDT_NOP (0x00000004)
    # FDT_END (0x00000009)
    
    # Let's write a simple parser for FDT_PROP to extract model, compatible, and wifi nodes
    model = "Unknown"
    compatible = []
    wifi_nodes = []
    
    struct_data = data[off_dt_struct:off_dt_struct+size_dt_struct]
    idx = 0
    node_stack = []
    
    while idx < len(struct_data):
        token = struct.unpack('>I', struct_data[idx:idx+4])[0]
        idx += 4
        
        if token == 1: # FDT_BEGIN_NODE
            # Null-terminated node name
            name_bytes = []
            while struct_data[idx] != 0:
                name_bytes.append(struct_data[idx])
                idx += 1
            idx += 1
            # Align to 4 bytes
            idx = (idx + 3) & ~3
            node_name = bytes(name_bytes).decode('ascii', errors='ignore')
            node_stack.append(node_name)
            
            if any(term in node_name.lower() for term in ['wifi', 'sdio', 'wireless', 'wlan', 'broadcom', 'realtek']):
                wifi_nodes.append("/" + "/".join(node_stack))
                
        elif token == 2: # FDT_END_NODE
            if node_stack:
                node_stack.pop()
                
        elif token == 3: # FDT_PROP
            val_len, name_off = struct.unpack('>II', struct_data[idx:idx+8])
            idx += 8
            prop_val = struct_data[idx:idx+val_len]
            idx += val_len
            idx = (idx + 3) & ~3
            
            # Get property name from strings block
            prop_name = ""
            # find string in strings_data at name_off
            p_end = strings_data.find(b'\x00', name_off)
            if p_end != -1:
                prop_name = strings_data[name_off:p_end].decode('ascii', errors='ignore')
                
            # If property is model or compatible and we are in root node
            if len(node_stack) == 1 and node_stack[0] == "":
                if prop_name == "model":
                    model = prop_val.strip(b'\x00').decode('ascii', errors='ignore')
                elif prop_name == "compatible":
                    # extract list of null-terminated strings
                    parts = prop_val.split(b'\x00')
                    compatible = [p.decode('ascii', errors='ignore') for p in parts if p]
                    
        elif token == 4: # FDT_NOP
            pass
        elif token == 9: # FDT_END
            break
            
    print(f"  Model: {model}")
    print(f"  Compatible: {compatible}")
    if wifi_nodes:
        print(f"  Found wifi-related nodes: {wifi_nodes}")
    else:
        print(f"  No wifi-related nodes found in node names.")
        
    return {
        'model': model,
        'compatible': compatible,
        'wifi_nodes': wifi_nodes,
        'size': totalsize
    }

print("=== Mainline DTB ===")
mainline = parse_dtb(r"f:\dtb\amlogic\meson-gxl-s905x-p212.dtb")
print("\n=== WiFi DTB (from forums) ===")
wifi_dtb = parse_dtb(r"d:\STB_B860H\04-file-dtb-wifi\meson-gxl-s905x-p212.dtb")
