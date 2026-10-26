#!/usr/bin/env bash
# Download the Ophub Armbian image and unpack it into the destination directory.
# Replaces tools/download_and_prep_image.py (plain HTTPS fetch needs no Python).
# Usage: bash tools/download_image.sh [dest_dir] (default: current directory;
#   e.g. bash tools/download_image.sh D:/ to use a drive root as in the guide)
set -euo pipefail

URL="https://github.com/ophub/amlogic-s9xxx-armbian/releases/download/Armbian_bookworm_arm64_server_2026.10/Armbian_26.11.0_amlogic_s905x-b860h_bookworm_6.12.112_server_2026.10.15.img.gz"
DEST_DIR="${1:-.}"
GZ_FILE="${DEST_DIR}/Armbian_b860h.img.gz"
IMG_FILE="${DEST_DIR}/Armbian_b860h.img"

if [ -f "$IMG_FILE" ]; then
  echo "$IMG_FILE already exists ($(du -m "$IMG_FILE" | cut -f1) MB). Skipping download."
  exit 0
fi

echo "Downloading to $GZ_FILE ..."
curl -L --progress-bar -o "$GZ_FILE" "$URL"
echo "Verifying checksum (best effort) ..."
if curl -sfL -o "$GZ_FILE.sha256" "$URL.sha256"; then
  (cd "$(dirname "$GZ_FILE")" && sha256sum -c "$(basename "$GZ_FILE").sha256") || { echo "CHECKSUM MISMATCH — delete $GZ_FILE and retry."; exit 1; }
else
  echo "WARNING: no .sha256 published upstream; skipping verification."
fi
echo "Decompressing to $IMG_FILE ..."
gunzip -c "$GZ_FILE" > "$IMG_FILE"
rm -f "$GZ_FILE"
echo "Done: $IMG_FILE ($(du -m "$IMG_FILE" | cut -f1) MB)."
