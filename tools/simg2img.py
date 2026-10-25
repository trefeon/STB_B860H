#!/usr/bin/env python3
"""
Pure Python simg2img (Android Sparse to Raw ext4 Image Converter)
Fast, standalone, zero dependencies.

Usage:
  python tools/simg2img.py <input.sparse.img> <output.raw.img>
"""

import sys
import struct
import os
import time

SPARSE_HEADER_MAGIC = 0xED26FF3A
CHUNK_TYPE_RAW = 0xCAC1
CHUNK_TYPE_FILL = 0xCAC2
CHUNK_TYPE_DONT_CARE = 0xCAC3
CHUNK_TYPE_CRC32 = 0xCAC4

def simg2img(in_path, out_path):
    print(f"[simg2img] Reading sparse image: {in_path}")
    start = time.time()
    
    with open(in_path, "rb") as in_f, open(out_path, "wb") as out_f:
        header = in_f.read(28)
        if len(header) < 28:
            print("ERROR: File too small to be a sparse image.")
            return False
            
        magic, major, minor, file_hdr_sz, chunk_hdr_sz, blk_sz, total_blks, total_chunks, image_checksum = struct.unpack("<IHHHHIIII", header)
        
        if magic != SPARSE_HEADER_MAGIC:
            print(f"ERROR: Invalid sparse magic 0x{magic:08x}. Not an Android sparse image.")
            return False
            
        print(f"  Block size: {blk_sz} bytes")
        print(f"  Total blocks: {total_blks} ({total_blks * blk_sz / 1024 / 1024:.1f} MB output size)")
        print(f"  Total chunks: {total_chunks}")
        
        # Skip any extra header bytes
        if file_hdr_sz > 28:
            in_f.seek(file_hdr_sz)
            
        out_pos = 0
        last_print = time.time()
        
        for c in range(total_chunks):
            chunk_hdr = in_f.read(12)
            if len(chunk_hdr) < 12:
                break
            chunk_type, reserved1, chunk_sz, total_sz = struct.unpack("<HHII", chunk_hdr)
            data_sz = total_sz - chunk_hdr_sz
            
            if chunk_type == CHUNK_TYPE_RAW:
                raw_bytes = chunk_sz * blk_sz
                # Copy in 1MB chunks
                remaining = raw_bytes
                while remaining > 0:
                    batch = min(remaining, 1024 * 1024)
                    buf = in_f.read(batch)
                    out_f.write(buf)
                    remaining -= len(buf)
                out_pos += raw_bytes
            elif chunk_type == CHUNK_TYPE_FILL:
                fill_val = in_f.read(4)
                fill_pattern = fill_val * (blk_sz // 4)
                for _ in range(chunk_sz):
                    out_f.write(fill_pattern)
                out_pos += chunk_sz * blk_sz
            elif chunk_type == CHUNK_TYPE_DONT_CARE:
                # Seek forward (sparse file / hole)
                skip_bytes = chunk_sz * blk_sz
                out_f.seek(skip_bytes, os.SEEK_CUR)
                out_pos += skip_bytes
            elif chunk_type == CHUNK_TYPE_CRC32:
                in_f.read(4)
            else:
                print(f"WARN: Unknown chunk type 0x{chunk_type:04x} at chunk {c}")
                
            if time.time() - last_print > 3:
                percent = (c + 1) / total_chunks * 100
                print(f"  Progress: {percent:.1f}% ({c+1}/{total_chunks} chunks)")
                last_print = time.time()
                
        # Ensure final file size matches total_blks * blk_sz
        expected_size = total_blks * blk_sz
        if out_f.tell() < expected_size:
            out_f.truncate(expected_size)

    elapsed = time.time() - start
    out_size = os.path.getsize(out_path)
    print(f"[SUCCESS] Converted in {elapsed:.1f}s! Output raw image: {out_size} bytes ({out_size/1024/1024:.1f} MB)")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python simg2img.py <input.sparse.img> <output.raw.img>")
        sys.exit(1)
    simg2img(sys.argv[1], sys.argv[2])
