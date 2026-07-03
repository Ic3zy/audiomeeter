import sys
import asyncio
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from gui import Window
from core import Engine

from base import Ctx

from core.cython_core.audio_core import (
    init_audio_system,
    free_audio_system,
    AudioRecorder,
    Distributor
)

import time
async def tasks():
    print("tasks started")
    try:
        init_audio_system()
        devices = ["input_main", "input_aux"]
        name_to_id = {"input_main": "alsa_output.usb-XiiSound_Technology_Corporation_Fuxi-H7-00.analog-stereo.monitor", "input_aux": "audiomeeter-aux-input.monitor"}

        distributor = Ctx["distributor"]
        devicess = []
        for device in devices:
            print(f"device: {device}, id: {name_to_id[device]}")
            a = distributor.create_listen_device(name_to_id[device], device)
            a.start()
            devicess.append(a)
        print(f"devices: {devicess}")
    except Exception as e:
        print(f"tasks error: {e}")
    finally:
        print("tasks finished")

def main():
    Ctx["distributor"] = Distributor()
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
    task2 = loop.create_task(tasks())
    


    def on_quit():
        if not task.done():
            task.cancel()
            
    app.aboutToQuit.connect(on_quit)
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()