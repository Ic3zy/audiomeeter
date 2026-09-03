#!/usr/bin/env bash
# Launcher script for AudioMeeter
cd /usr/share/audiomeeter
exec python3 src/main.py "$@"
