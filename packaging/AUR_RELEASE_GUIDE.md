# AudioMeeter AUR Release Guide (Arch User Repository)

This document explains how to publish and maintain **AudioMeeter** on the Arch User Repository (AUR).

---

## Prerequisites

1. An account on [aur.archlinux.org](https://aur.archlinux.org/).
2. Your SSH public key added to your AUR account settings (`~/.ssh/id_ed25519.pub`).

---

## Step 1: Create a GitHub Release Tag

Before publishing to AUR, tag your git commit on GitHub:

```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

---

## Step 2: Initialize AUR Repository (First-Time Only)

Clone your package space from AUR:

```bash
ssh -T aur@aur.archlinux.org
git clone aur@aur.archlinux.org:audiomeeter.git
```

---

## Step 3: Copy Packaging Files & Update .SRCINFO

Copy `PKGBUILD`, `audiomeeter.desktop`, `audiomeeter.sh` into your cloned `audiomeeter` AUR directory:

```bash
cp packaging/PKGBUILD audiomeeter/
cp packaging/audiomeeter.desktop audiomeeter/
cp packaging/audiomeeter.sh audiomeeter/

cd audiomeeter
makepkg --printsrcinfo > .SRCINFO
```

---

## Step 4: Commit & Push to AUR

```bash
git add PKGBUILD .SRCINFO audiomeeter.desktop audiomeeter.sh
git commit -m "Publish AudioMeeter v1.0.0"
git push origin master
```

---

## Step 5: Verify Installation

Users can now install your application on any Arch-based distribution with a single command:

```bash
paru -S audiomeeter
# or
yay -S audiomeeter
```

During installation, `paru`/`yay` will automatically:
1. Pull all required dependencies (`pipewire`, `pyside6`, `python-pulsectl`, `python-evdev`, `python-qasync`, etc.) from official Arch repositories.
2. Compile C shared libraries and Cython extensions natively on the user's system using their exact active Python version.
3. Install the application, executable wrapper, desktop icon, and menu launcher.
