import os
import glob
import ctypes
import sys
import pyximport
from setuptools import Extension

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
C_DIR = os.path.join(CURRENT_DIR, "C", "audio_core")
WVOSD_C_DIR = os.path.join(CURRENT_DIR, "C", "wayland-volume-osd")

# Shared Kütüphaneleri (Shared Libraries) Dinamik Olarak Yükle
_libengine_path = os.path.join(C_DIR, "libengine.so")
if os.path.exists(_libengine_path):
    ctypes.CDLL(_libengine_path)

_libosd_path = os.path.join(WVOSD_C_DIR, "libosd.so")
if os.path.exists(_libosd_path):
    ctypes.CDLL(_libosd_path)

# Engine Uzantısı
engine_ext = Extension(
    name="core.engine",
    sources=[os.path.join(CURRENT_DIR, "engine.pyx")],
    include_dirs=[
        os.path.join(C_DIR, "include"),
        "/usr/include/pipewire-0.3",
        "/usr/include/spa-0.2",
        os.path.join(CURRENT_DIR, "C", "rt_biquad", "include"),
    ],
    library_dirs=[C_DIR],
    libraries=["engine", "pipewire-0.3", "m"],
    runtime_library_dirs=[C_DIR],
    define_macros=[("_REENTRANT", None)],
    language="c",
)

# Wayland Volume OSD Uzantısı
wvosd_ext = Extension(
    name="core.wvosd",
    sources=[os.path.join(CURRENT_DIR, "wvosd.pyx")],
    include_dirs=[
        os.path.join(WVOSD_C_DIR, "include"),
        os.path.join(WVOSD_C_DIR, "src"),
        WVOSD_C_DIR,
    ],
    library_dirs=[WVOSD_C_DIR],
    libraries=["osd"],
    runtime_library_dirs=[WVOSD_C_DIR],
    language="c",
)

pyximport.install(
    build_in_temp=True,
    inplace=True,
    language_level=3,
    setup_args={"ext_modules": [engine_ext, wvosd_ext]},
)

from . import engine
from . import wvosd

from .main import Engine
from .devices import DevicesManager

__all__ = ["Engine", "DevicesManager", "engine", "wvosd"]
