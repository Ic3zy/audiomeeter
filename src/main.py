import sys
import asyncio
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from gui import Window
from core import Engine

import core.cython_core.audio_core

def main():
    app = QApplication(sys.argv)
    
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    engine = Engine()
    window = Window()
    window.show()
    
    task = loop.create_future()
    
    async def engine_runner():
        try:
            await engine.run()
        except asyncio.CancelledError:
            pass
    
    task = loop.create_task(engine_runner())
    
    def on_quit():
        if not task.done():
            task.cancel()
            
    app.aboutToQuit.connect(on_quit)
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()