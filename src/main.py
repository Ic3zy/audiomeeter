import os
import asyncio
import argparse
import signal
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from qasync import QEventLoop

from gui import Window
from core import Engine

from base import Ctx


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-config", action="store_true")
    parser.add_argument("--reset-config", action="store_true")
    parser.add_argument("--no-gui", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    QApplication.setDesktopFileName("audiomeeter")
    app = QApplication()

    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "AudioMeeter_Icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    engine = Engine()

    if not args.no_gui:
        window = Window()
        window.show()

    task = loop.create_future()

    async def initialize():
        await asyncio.sleep(0.01)
        await engine.run()
        await asyncio.sleep(0.1)

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

    def handle_sigint():
        app.quit()

    try:
        loop.add_signal_handler(signal.SIGINT, handle_sigint)
    except NotImplementedError:
        # Not implemented on Windows OS
        pass

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
