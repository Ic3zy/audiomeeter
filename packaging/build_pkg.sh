#!/usr/bin/env bash
# AudioMeeter Package Builder Script for Arch Linux / Paru / Pacman

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo " AudioMeeter Arch Linux Package Builder "
echo "=========================================="

if command -v paru >/dev/null 2>&1; then
    echo "[+] Building package with paru..."
    paru -Ui .
elif command -v makepkg >/dev/null 2>&1; then
    echo "[+] Building package with makepkg..."
    makepkg -si --noconfirm
else
    echo "[-] Error: Neither paru nor makepkg found!"
    exit 1
fi

echo "=========================================="
echo " Build & Installation Completed! "
echo "=========================================="
