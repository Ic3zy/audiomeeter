import asyncio
from evdev import UInput, ecodes


class ConsumerListener:
    def __init__(self, device):
        self.device = device
        self.uinput = UInput.from_device(device)
        self.callback = None

    def add_callback(self, callback):
        self.callback = callback

    def remove_callback(self, callback):
        self.callback = None

    def _on_event(self, device):
        try:
            for event in device.read():
                if self.callback is not None:
                    if not self.callback(event):
                        self.uinput.write_event(event)

                        if event.type == ecodes.EV_SYN:
                            self.uinput.syn()

                else:
                    print("ConsumerListener: No callback set.")

        except BlockingIOError:
            pass

    def start(self):
        self.device.grab()

        loop = asyncio.get_running_loop()
        loop.add_reader(self.device.fd, self._on_event, self.device)

    def stop(self):
        loop = asyncio.get_running_loop()
        loop.remove_reader(self.device.fd)
        self.device.ungrab()

    def __del__(self):
        try:
            self.stop()
        except (RuntimeError, AttributeError, OSError):
            pass
