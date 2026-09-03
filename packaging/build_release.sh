#!/usr/bin/env bash
# AudioMeeter Release Package Generator
# Generates a standalone .pkg.tar.zst binary package for GitHub Releases

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$SCRIPT_DIR"

echo "=================================================="
echo " AudioMeeter - Building Binary Release Package    "
echo "=================================================="

# 1. Clean old build artifacts
rm -rf pkg src *.pkg.tar.zst

# 2. Build C shared libraries
echo "[1/3] Compiling C shared libraries..."
make -C "$PROJECT_ROOT/src/core/C/audio_core" clean
make -C "$PROJECT_ROOT/src/core/C/audio_core"
make -C "$PROJECT_ROOT/src/core/C/wayland-volume-osd" clean
make -C "$PROJECT_ROOT/src/core/C/wayland-volume-osd" libosd.so

# 3. Create .pkg.tar.zst binary package using makepkg
echo "[2/3] Generating Arch Pacman binary package (.pkg.tar.zst)..."
makepkg -f --nodeps

echo "[3/3] Release package ready!"
echo "--------------------------------------------------"
ls -lh *.pkg.tar.zst
echo "--------------------------------------------------"
echo "Upload the .pkg.tar.zst file above directly to GitHub Releases."
echo "Users can install it without cloning using:"
echo "  sudo pacman -U audiomeeter-1.0.0-1-x86_64.pkg.tar.zst"
echo "=================================================="
