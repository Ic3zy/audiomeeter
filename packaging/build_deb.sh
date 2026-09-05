#!/usr/bin/env bash
set -e

# Usage: ./packaging/build_deb.sh [TAG_NAME]
TAG=${1:-"v1.0.0"}

# Extract clean debian-compatible version (must start with digit, no underscores allowed)
CLEAN_VER=$(echo "$TAG" | sed 's/^v//' | tr '_' '.')

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Building AudioMeeter Debian/Ubuntu (.deb) Package ==="
echo "[1/4] Version: $CLEAN_VER"

cd "$PROJECT_ROOT"

# NOTE: C shared libraries are NOT compiled here.
# They are compiled on the USER's machine via DEBIAN/postinst
# to ensure GLIBC compatibility across all distro versions.

# Prepare staging dir
STAGE_DIR="$PROJECT_ROOT/packaging/deb_staging"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR/DEBIAN"
mkdir -p "$STAGE_DIR/usr/share/audiomeeter"
mkdir -p "$STAGE_DIR/usr/bin"
mkdir -p "$STAGE_DIR/usr/share/applications"
mkdir -p "$STAGE_DIR/usr/share/pixmaps"
mkdir -p "$STAGE_DIR/usr/share/icons/hicolor/512x512/apps"
mkdir -p "$STAGE_DIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$STAGE_DIR/usr/share/icons/hicolor/128x128/apps"
mkdir -p "$STAGE_DIR/usr/share/icons/hicolor/64x64/apps"
mkdir -p "$STAGE_DIR/usr/share/icons/hicolor/48x48/apps"
mkdir -p "$STAGE_DIR/usr/share/icons/hicolor/scalable/apps"

# Copy source code (exclude pre-built .so files)
cp -r src "$STAGE_DIR/usr/share/audiomeeter/"
# Remove any pre-built .so files so we don't ship cross-distro binaries
find "$STAGE_DIR/usr/share/audiomeeter/src" -name '*.so' -delete

# Copy icon files if available
if [ -f "packaging/AudioMeeter_Icon.png" ]; then
    cp packaging/AudioMeeter_Icon.png "$STAGE_DIR/usr/share/pixmaps/audiomeeter.png"
    cp packaging/AudioMeeter_Icon.png "$STAGE_DIR/usr/share/icons/hicolor/512x512/apps/audiomeeter.png"
    cp packaging/AudioMeeter_Icon.png "$STAGE_DIR/usr/share/icons/hicolor/256x256/apps/audiomeeter.png"
    cp packaging/AudioMeeter_Icon.png "$STAGE_DIR/usr/share/icons/hicolor/128x128/apps/audiomeeter.png"
    cp packaging/AudioMeeter_Icon.png "$STAGE_DIR/usr/share/icons/hicolor/64x64/apps/audiomeeter.png"
    cp packaging/AudioMeeter_Icon.png "$STAGE_DIR/usr/share/icons/hicolor/48x48/apps/audiomeeter.png"
    cp packaging/AudioMeeter_Icon.png "$STAGE_DIR/usr/share/icons/hicolor/scalable/apps/audiomeeter.png"
fi

# Copy launcher and desktop file
cp packaging/audiomeeter.sh "$STAGE_DIR/usr/bin/audiomeeter"
chmod 755 "$STAGE_DIR/usr/bin/audiomeeter"
cp packaging/audiomeeter.desktop "$STAGE_DIR/usr/share/applications/audiomeeter.desktop"
chmod 644 "$STAGE_DIR/usr/share/applications/audiomeeter.desktop"

# Create DEBIAN/control
cat << EOF > "$STAGE_DIR/DEBIAN/control"
Package: audiomeeter
Version: $CLEAN_VER
Section: sound
Priority: optional
Architecture: amd64
Maintainer: AudioMeeter Team <dev@audiomeeter.org>
Depends: python3, pipewire, libpipewire-0.3-dev, libcairo2, libcairo2-dev, libwayland-dev, libwayland-bin, python3-pyside6.qtcore, python3-pyside6.qtgui, python3-pyside6.qtwidgets, python3-psutil, python3-evdev, python3-pulsectl, python3-qasync, gcc, make, cython3, python3-setuptools
Description: Virtual Audio Mixer for Linux using PipeWire and Qt
 High-performance virtual audio routing, volume control, and OSD overlay for PipeWire.
EOF

# Create DEBIAN/postinst - compiles C libraries on the USER's machine after install
cat << 'POSTINST' > "$STAGE_DIR/DEBIAN/postinst"
#!/usr/bin/env bash
set -e
SRC="/usr/share/audiomeeter/src/core/C"
echo "[AudioMeeter] Compiling audio engine for your system (one-time setup)..."
make -C "$SRC/audio_core" clean 2>/dev/null || true
make -C "$SRC/audio_core"
make -C "$SRC/wayland-volume-osd" clean 2>/dev/null || true
make -C "$SRC/wayland-volume-osd" libosd.so
echo "[AudioMeeter] Build complete."
POSTINST
chmod 755 "$STAGE_DIR/DEBIAN/postinst"

# Create DEBIAN/prerm - cleans compiled .so files on removal
cat << 'PRERM' > "$STAGE_DIR/DEBIAN/prerm"
#!/usr/bin/env bash
set -e
SRC="/usr/share/audiomeeter/src/core/C"
make -C "$SRC/audio_core" clean 2>/dev/null || true
make -C "$SRC/wayland-volume-osd" clean 2>/dev/null || true
PRERM
chmod 755 "$STAGE_DIR/DEBIAN/prerm"

OUT_DEB="$PROJECT_ROOT/packaging/audiomeeter_${TAG}_amd64.deb"
rm -f "$OUT_DEB"

echo "[2/4] Packaging .deb..."
if command -v dpkg-deb >/dev/null 2>&1; then
    dpkg-deb --build "$STAGE_DIR" "$OUT_DEB"
else
    # Fallback using tar & ar if dpkg-deb is not installed locally
    DEB_TMP="$PROJECT_ROOT/packaging/deb_tmp"
    rm -rf "$DEB_TMP"
    mkdir -p "$DEB_TMP"
    echo "2.0" > "$DEB_TMP/debian-binary"
    (cd "$STAGE_DIR/DEBIAN" && tar -czf "$DEB_TMP/control.tar.gz" .)
    (cd "$STAGE_DIR" && tar --exclude='./DEBIAN' -czf "$DEB_TMP/data.tar.gz" .)
    (cd "$DEB_TMP" && ar rcs "$OUT_DEB" debian-binary control.tar.gz data.tar.gz)
    rm -rf "$DEB_TMP"
fi

rm -rf "$STAGE_DIR"

echo "[3/4] Release .deb package ready!"
echo "--------------------------------------------------"
ls -lh "$OUT_DEB"
echo "--------------------------------------------------"
echo "Package created at: $OUT_DEB"
echo ""
echo "NOTE: C libraries will be compiled on the user's machine at install time (postinst)."
