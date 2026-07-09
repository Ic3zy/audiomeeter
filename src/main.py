import sys
import asyncio
import argparse
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from gui import Window
from core import Engine

from base import Ctx

from core.cython_core.audio_core import (
    Distributor
)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-config", action="store_true")
    parser.add_argument("--reset-config", action="store_true")
    parser.add_argument("--no-gui", action="store_true")
    return parser.parse_args()

def main():
    args = parse_args()
    Ctx["distributor"] = Distributor()
    app = QApplication()
    
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    engine = Engine()

    # currently is not working
    if not args.no_gui:
        window = Window()
        window.show()
    
    task = loop.create_future()
    
    async def initialize():
        await asyncio.sleep(0.01)
        await engine.run()
        await asyncio.sleep(0.05)
            
        if args.reset_config:
            Ctx.reset_config()

        if not args.no_config:
            Ctx.load_config()
                
    
    task = loop.create_task(initialize())

    def on_quit():
        if not args.no_config:
            Ctx.on_quit()

        if not task.done():
            task.cancel()
            
    app.aboutToQuit.connect(on_quit)
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()