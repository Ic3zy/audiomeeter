import os
import pyximport

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
C_DIR = os.path.join(BASE_DIR, "C")

pyximport.install(
    setup_args={
        "include_dirs": [
            os.path.join(C_DIR, "include"),
            "/usr/include/pipewire-0.3",
            "/usr/include/spa-0.2",
        ],
        "library_dirs": [C_DIR],
        "libraries": ["engine", "pipewire-0.3", "m"],
        "runtime_library_dirs": [C_DIR],
        "define_macros": [("_REENTRANT", None)],
    },
    language_level=3,
)

from src.core import engine