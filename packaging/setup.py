import os
import subprocess
from setuptools import setup, Extension
from setuptools.command.build_py import build_py as _build_py
import pyximport

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
C_DIR = os.path.join(SRC_DIR, "core", "C", "audio_core")
WVOSD_C_DIR = os.path.join(SRC_DIR, "core", "C", "wayland-volume-osd")

def build_c_libraries():
    print("[AudioMeeter Build] Compiling C shared libraries...")
    subprocess.check_call(["make", "-C", C_DIR, "clean"])
    subprocess.check_call(["make", "-C", C_DIR])
    subprocess.check_call(["make", "-C", WVOSD_C_DIR, "clean"])
    subprocess.check_call(["make", "-C", WVOSD_C_DIR, "libosd.so"])

class CustomBuildPy(_build_py):
    def run(self):
        build_c_libraries()
        super().run()

engine_ext = Extension(
    name="src.core.engine",
    sources=[os.path.join(SRC_DIR, "core", "engine.pyx")],
    include_dirs=[
        os.path.join(C_DIR, "include"),
        "/usr/include/pipewire-0.3",
        "/usr/include/spa-0.2",
        os.path.join(SRC_DIR, "core", "C", "rt_biquad", "include"),
    ],
    library_dirs=[C_DIR],
    libraries=["engine", "pipewire-0.3", "m"],
    runtime_library_dirs=[C_DIR],
    define_macros=[("_REENTRANT", None)],
    language="c",
)

wvosd_ext = Extension(
    name="src.core.wvosd",
    sources=[os.path.join(SRC_DIR, "core", "wvosd.pyx")],
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

setup(
    name="audiomeeter",
    version="1.0.0",
    description="Virtual Audio Mixer for Linux using PipeWire and Qt",
    author="AudioMeeter Team",
    cmdclass={"build_py": CustomBuildPy},
    ext_modules=[engine_ext, wvosd_ext],
    install_requires=[
        "PySide6",
        "qasync",
        "pulsectl",
        "psutil",
        "evdev",
        "cython",
    ],
)
