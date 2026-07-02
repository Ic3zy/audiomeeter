import os
import pyximport

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(CURRENT_DIR, "build")

pyximport.install(
    inplace=True,
    build_dir=BUILD_DIR,
    language_level=3,
)