import os
import glob
import ctypes
import sys
import subprocess
import importlib.util
import pyximport.pyxbuild as pyxbuild
from setuptools import Extension

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
C_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "C", "audio_core"))
WVOSD_C_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "C", "wayland-volume-osd"))

# 1. Automatic build of C Shared Libraries if missing
_libengine_path = os.path.join(C_DIR, "libengine.so")
if not os.path.exists(_libengine_path):
    print("[AudioCore] Building libengine.so...")
    try:
        subprocess.check_call(["make", "-C", C_DIR])
    except Exception as e:
        print(f"[AudioCore] Error building libengine.so: {e}")

_libosd_path = os.path.join(WVOSD_C_DIR, "libosd.so")
if not os.path.exists(_libosd_path):
    print("[AudioOSD] Building libosd.so...")
    try:
        subprocess.check_call(["make", "-C", WVOSD_C_DIR, "libosd.so"])
    except Exception as e:
        print(f"[AudioOSD] Error building libosd.so: {e}")

# 2. Shared Libraries Load
if os.path.exists(_libengine_path):
    ctypes.CDLL(_libengine_path, mode=ctypes.RTLD_GLOBAL)

if os.path.exists(_libosd_path):
    ctypes.CDLL(_libosd_path, mode=ctypes.RTLD_GLOBAL)

# 3. User-writable Cython Build Directory
PYXBUILD_DIR = os.path.expanduser("~/.cache/audiomeeter/cython")
os.makedirs(PYXBUILD_DIR, exist_ok=True)

engine_ext = Extension(
    name="engine",
    sources=[os.path.join(CURRENT_DIR, "engine.pyx")],
    include_dirs=[
        os.path.join(C_DIR, "include"),
        C_DIR,
        "/usr/include/pipewire-0.3",
        "/usr/include/spa-0.2",
        os.path.join(CURRENT_DIR, "C", "rt_biquad", "include"),
    ],
    library_dirs=[C_DIR],
    libraries=["engine", "pipewire-0.3", "m"],
    extra_link_args=[f"-Wl,-rpath,{C_DIR}"],
    define_macros=[("_REENTRANT", None)],
    language="c",
)

wvosd_ext = Extension(
    name="wvosd",
    sources=[os.path.join(CURRENT_DIR, "wvosd.pyx")],
    include_dirs=[
        os.path.join(WVOSD_C_DIR, "include"),
        os.path.join(WVOSD_C_DIR, "src"),
        WVOSD_C_DIR,
    ],
    library_dirs=[WVOSD_C_DIR],
    libraries=["osd"],
    extra_link_args=[f"-Wl,-rpath,{WVOSD_C_DIR}"],
    language="c",
)

def _load_or_build_cython(module_name, pyx_file, extension_mod):
    so_path = pyxbuild.pyx_to_dll(
        pyx_file,
        extension_mod,
        build_in_temp=True,
        pyxbuild_dir=PYXBUILD_DIR,
    )
    spec = importlib.util.spec_from_file_location(f"core.{module_name}", so_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"core.{module_name}"] = mod
    spec.loader.exec_module(mod)
    return mod

engine = _load_or_build_cython("engine", os.path.join(CURRENT_DIR, "engine.pyx"), engine_ext)
wvosd = _load_or_build_cython("wvosd", os.path.join(CURRENT_DIR, "wvosd.pyx"), wvosd_ext)

from .main import Engine
from .devices import DevicesManager

__all__ = ["Engine", "DevicesManager", "engine", "wvosd"]
