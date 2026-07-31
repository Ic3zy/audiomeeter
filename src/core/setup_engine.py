from setuptools import setup, Extension
from Cython.Build import cythonize
import os

C_DIR = os.path.join(os.path.dirname(__file__), "C")

ext = Extension(
    name="src.core.engine",
    sources=["src/core/engine.pyx"],
    include_dirs=[
        os.path.join(C_DIR, "include"),
        "/usr/include/pipewire-0.3",
        "/usr/include/spa-0.2",
    ],
    library_dirs=[C_DIR],
    libraries=["engine", "pipewire-0.3", "m"],
    runtime_library_dirs=[C_DIR],
    define_macros=[("_REENTRANT", None)],
    language="c",
)

setup(
    name="audiomeeter-engine",
    ext_modules=cythonize([ext], language_level="3"),
)
