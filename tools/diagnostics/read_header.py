import gzip
import struct
import os
import sys

def find_and_read_header_in_gz(gz_filepath):
    if not os.path.exists(gz_filepath):
        print(f"File not found: {gz_filepath}")
        return
        
    print(f"Scanning {gz_filepath} for ARM64 kernel Image magic...")
    magic_bytes = b'ARM\x64'  # 0x41 0x52 0x4d 0x64
    
    # Decompress stream-wise
    with gzip.open(gz_filepath, 'rb') as f:
        chunk_size = 1024 * 1024 * 4  # 4MB chunks
        buffer = b''
        offset = 0
        
        # Scan up to 800MB
        for i in range(200):
            chunk = f.read(chunk_size)
            if not chunk:
                break
            buffer += chunk
            
            # Find magic_bytes in buffer
            idx = buffer.find(magic_bytes)
            while idx != -1:
                # The header starts 56 bytes before the magic bytes
                header_start = idx - 56
                if header_start >= 0:
                    header = buffer[header_start:header_start+64]
                    if len(header) == 64:
                        code0, code1, text_offset, image_size, flags, res2, res3, res4, magic, res5 = struct.unpack('<IIQQQQQQII', header)
                        if magic == 0x644d5241:
                            print(f"Found ARM64 kernel Image at decompressed offset: {offset + header_start} bytes ({(offset + header_start)/(1024*1024):.2f} MB)")
                            print(f"  Magic: 0x{magic:08x}")
                            print(f"  Text Offset: 0x{text_offset:x}")
                            print(f"  Image Size:  0x{image_size:x} ({image_size} bytes)")
                            print(f"  Flags:       0x{flags:x}")
                            # Keep searching to see if there are multiple or if this is the only one
                idx = buffer.find(magic_bytes, idx + 1)
                
            buffer = buffer[-256:]  # keep overlap
            offset += chunk_size - 256
            
    print("Scan complete.")

if len(sys.argv) < 2:
    sys.exit(f"Usage: {sys.argv[0]} <image.img.gz>")
find_and_read_header_in_gz(sys.argv[1])
