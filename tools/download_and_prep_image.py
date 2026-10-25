import urllib.request
import gzip
import shutil
import os
import time
import sys

URL = "https://github.com/ophub/amlogic-s9xxx-armbian/releases/download/Armbian_bookworm_arm64_server_2026.10/Armbian_26.11.0_amlogic_s905x-b860h_bookworm_6.12.112_server_2026.10.15.img.gz"
GZ_FILE = "D:/Armbian_b860h.img.gz"
IMG_FILE = "D:/Armbian_b860h.img"

def download():
    if os.path.exists(IMG_FILE):
        print(f"{IMG_FILE} already exists ({os.path.getsize(IMG_FILE)/(1024*1024):.1f} MB). Skipping download.")
        return

    print(f"Downloading from {URL} to {GZ_FILE}...")
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
    start = time.time()
    last_print = start
    downloaded = 0
    with urllib.request.urlopen(req, timeout=30) as resp, open(GZ_FILE, 'wb') as f:
        total = int(resp.headers.get('Content-Length', 0))
        while True:
            chunk = resp.read(4 * 1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            now = time.time()
            if now - last_print >= 5:
                pct = (downloaded / total * 100) if total else 0
                speed = (downloaded / (1024 * 1024)) / (now - start)
                print(f"Downloaded {downloaded/(1024*1024):.1f}/{total/(1024*1024):.1f} MB ({pct:.1f}%) at {speed:.2f} MB/s")
                last_print = now
    
    print(f"Download complete! Time: {time.time()-start:.1f}s")
    print(f"Decompressing {GZ_FILE} to {IMG_FILE}...")
    start_dec = time.time()
    with gzip.open(GZ_FILE, 'rb') as f_in, open(IMG_FILE, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out, length=8*1024*1024)
    print(f"Decompression complete! ({os.path.getsize(IMG_FILE)/(1024*1024):.1f} MB) in {time.time()-dec_start if 'dec_start' in locals() else time.time()-start_dec:.1f}s")
    if os.path.exists(GZ_FILE):
        os.remove(GZ_FILE)

if __name__ == "__main__":
    download()
