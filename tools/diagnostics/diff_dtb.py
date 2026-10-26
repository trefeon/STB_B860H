import struct
import os
import sys

def dump_nodes(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return {}
        
    with open(filepath, 'rb') as f:
        data = f.read()
        
    magic, totalsize, off_dt_struct, off_dt_strings, off_mem_rsvmap, version, last_comp_version, boot_cpuid_phys, size_dt_strings, size_dt_struct = struct.unpack('>IIIIIIIIII', data[:40])
    
    strings_data = data[off_dt_strings:off_dt_strings+size_dt_strings]
    struct_data = data[off_dt_struct:off_dt_struct+size_dt_struct]
    
    idx = 0
    node_stack = []
    nodes = {}
    
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
            current_path = "/" + "/".join(node_stack)
            nodes[current_path] = {}
            
        elif token == 2: # FDT_END_NODE
            if node_stack:
                node_stack.pop()
                
        elif token == 3: # FDT_PROP
            val_len, name_off = struct.unpack('>II', struct_data[idx:idx+8])
            idx += 8
            prop_val = struct_data[idx:idx+val_len]
            idx += val_len
            idx = (idx + 3) & ~3
            
            p_end = strings_data.find(b'\x00', name_off)
            prop_name = strings_data[name_off:p_end].decode('ascii', errors='ignore')
            
            current_path = "/" + "/".join(node_stack)
            if current_path in nodes:
                nodes[current_path][prop_name] = prop_val
                
        elif token == 4: # FDT_NOP
            pass
        elif token == 9: # FDT_END
            break
            
    return nodes

def format_val(val):
    if len(val) == 0:
        return "empty"
    # Try as string
    if val[-1] == 0 and all(32 <= c < 127 or c == 0 for c in val[:-1]):
        parts = val.split(b'\x00')
        return ", ".join([p.decode('ascii', errors='ignore') for p in parts if p])
    # Try as u32s
    if len(val) % 4 == 0:
        u32s = struct.unpack(f'>{len(val)//4}I', val)
        # Check if they look like phandles or small numbers
        return " ".join([f"<{x}>" or f"0x{x:x}" for x in u32s])
    return f"bin:{val.hex()}"

def compare_nodes(mainline_nodes, wifi_nodes):
    # Let's find nodes related to MMC/SDIO or WiFi
    interesting_keys = []
    for k in mainline_nodes.keys() | wifi_nodes.keys():
        if any(term in k.lower() for term in ['mmc', 'sdio', 'wifi', 'pwrseq', 'pinctrl']):
            # Filter pinctrl to only show sdio related pins
            if 'pinctrl' in k.lower() and not any(t in k.lower() for t in ['sdio', 'wifi']):
                continue
            interesting_keys.append(k)
            
    interesting_keys.sort()
    
    for k in interesting_keys:
        in_m = k in mainline_nodes
        in_w = k in wifi_nodes
        
        if not in_m:
            print(f"\n[Node ONLY in WiFi DTB]: {k}")
            for p, v in wifi_nodes[k].items():
                print(f"  {p} = {format_val(v)}")
        elif not in_w:
            print(f"\n[Node ONLY in Mainline DTB]: {k}")
            for p, v in mainline_nodes[k].items():
                print(f"  {p} = {format_val(v)}")
        else:
            # Node in both, let's compare properties
            m_props = mainline_nodes[k]
            w_props = wifi_nodes[k]
            
            diffs = {}
            for p in m_props.keys() | w_props.keys():
                if p not in m_props:
                    diffs[p] = (None, w_props[p])
                elif p not in w_props:
                    diffs[p] = (m_props[p], None)
                elif m_props[p] != w_props[p]:
                    diffs[p] = (m_props[p], w_props[p])
                    
            if diffs:
                print(f"\n[Node Diffs]: {k}")
                for p, (v_m, v_w) in diffs.items():
                    if v_m is None:
                        print(f"  + {p} = {format_val(v_w)}")
                    elif v_w is None:
                        print(f"  - {p} = {format_val(v_m)}")
                    else:
                        print(f"  * {p}: Mainline: {format_val(v_m)} | WiFi: {format_val(v_w)}")

if len(sys.argv) < 3:
    sys.exit(f"Usage: {sys.argv[0]} <mainline.dtb> <other.dtb>")
m_nodes = dump_nodes(sys.argv[1])
w_nodes = dump_nodes(sys.argv[2])
compare_nodes(m_nodes, w_nodes)
