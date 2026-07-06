import os
import glob
import pyximport

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(CURRENT_DIR, "build")

PYX_FILE = os.path.join(CURRENT_DIR, "audio_core.pyx")

if os.path.exists(PYX_FILE):
    pyx_mod_time = os.path.getmtime(PYX_FILE)
    
    so_files = glob.glob(os.path.join(CURRENT_DIR, "*.so")) + glob.glob(os.path.join(CURRENT_DIR, "*.pyd"))
    
    for so_file in so_files:
        so_mod_time = os.path.getmtime(so_file)
        
        if pyx_mod_time > so_mod_time:
            try:
                os.remove(so_file)
            except Exception as e:
                print(f"[Cython Rebuild]: {e}")
                

pyximport.install(
    inplace=True,
    build_dir=BUILD_DIR,
    language_level=3,
)