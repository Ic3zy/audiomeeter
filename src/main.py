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
        devices = ["input_aux"]
        name_to_id = {"input_aux": "audiomeeter-aux-input.monitor"}

        distributor = Ctx["distributor"]
        b = None
        for device in devices:
            print(f"device: {device}, id: {name_to_id[device]}")
            a = distributor.create_listen_device(name_to_id[device], device)
            a.start()
            b = a
            break

        a = distributor.create_sink("alsa_output.usb-XiiSound_Technology_Corporation_Fuxi-H7-00.iec958-stereo", "a1")
        # a.listen_loop()
        distributor.create_bridge("input_aux", "a1")
        last_db_sink = 0
        last_db_aux = 0
        while True:
            dbsink = a.get_dB()
            if dbsink != last_db_sink:
                last_db_sink = dbsink
                Ctx["s_led_6"] = dbsink

            dbaux = b.dB
            if dbaux != last_db_aux:
                last_db_aux = dbaux
                Ctx["input_aux"] = dbaux
                print(f"dbaux: {dbaux}")

                
            await asyncio.sleep(0.2)

        print(f"devices: {devicess}")
    except Exception as e:
        print(f"tasks error: {e}")
        import traceback
        traceback.print_exc()
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