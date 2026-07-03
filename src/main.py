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
    AudioRecorder
)

import time
async def tasks():
    init_audio_system()

    mic_device = b"alsa_output.usb-XiiSound_Technology_Corporation_Fuxi-H7-00.analog-stereo.monitor"
    speaker_device = b"alsa_output.usb-XiiSound_Technology_Corporation_Fuxi-H7-00.analog-stereo.monitor"

    mic_recorder = AudioRecorder(mic_device, instance_id=1)
    speaker_recorder = AudioRecorder(speaker_device, instance_id=2)

    mic_recorder.start()
    speaker_recorder.start()
    count = 0 

    try:
        while True:
            await asyncio.sleep(0.2)
            print(f"Mic dB: {mic_recorder.dB} | Speaker dB: {speaker_recorder.dB}")
            count += 1

            if count > 5:
                t1 = time.perf_counter()
                Ctx["input_aux"] = mic_recorder.dB
                Ctx["input_main"] = mic_recorder.dB
                t2 = time.perf_counter()
                print(f"\n\n\n\naux: {t2 - t1}")
                count = 0
            else:
                Ctx["input_aux"] = mic_recorder.dB

    except KeyboardInterrupt:
        return
    finally:
        mic_recorder.stop()
        speaker_recorder.stop()
        free_audio_system()



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
    task2 = loop.create_task(tasks())
    


    def on_quit():
        if not task.done():
            task.cancel()
            
    app.aboutToQuit.connect(on_quit)
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    main()