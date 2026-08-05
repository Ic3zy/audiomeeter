import pulsectl, evdev


def sink_name_to_consumer_device(sink_name: str):
    for sink in DevicesManager.get_physical_sinks():
        if sink.name != sink_name:
            continue

        props = sink.raw.proplist

        vendor = props.get("device.vendor.id")
        product = props.get("device.product.id")

        if vendor is None or product is None:
            return None

        vendor = int(vendor, 16)
        product = int(product, 16)

        for path in evdev.list_devices():
            dev = evdev.InputDevice(path)

            if dev.info.vendor != vendor:
                continue

            if dev.info.product != product:
                continue

            caps = dev.capabilities(verbose=False)
            keys = caps.get(evdev.ecodes.EV_KEY, [])

            if evdev.ecodes.KEY_VOLUMEUP in keys or evdev.ecodes.KEY_VOLUMEDOWN in keys:
                return dev

        return None

    return None


class PulseOutputDevice:
    def __init__(self, sink_info):
        self.raw = sink_info
        self.index = sink_info.index
        self.name = sink_info.name
        self.description = sink_info.description

        self.is_our_virtual = "audiomeeter.device_type" in sink_info.proplist

        self.is_standard_virtual = sink_info.driver in [
            "module-null-sink.c",
            "module-virtual-sink.c",
            "module-remap-sink.c",
            "module-combine-sink.c",
        ]

        self.physical = not self.is_our_virtual and not self.is_standard_virtual

        self._consumer_device = None
        self._consumer_searched = False

    @property
    def is_physical(self) -> bool:
        return self.physical

    @property
    def is_virtual(self) -> bool:
        return self.is_our_virtual or self.is_standard_virtual

    @property
    def consumer_device(self):
        if self._consumer_searched:
            return self._consumer_device

        self._consumer_searched = True

        if not self.is_physical:
            return None

        props = self.raw.proplist

        vendor = props.get("device.vendor.id")
        product = props.get("device.product.id")

        if vendor is None or product is None:
            return None

        vendor = int(vendor, 16)
        product = int(product, 16)

        for path in evdev.list_devices():
            dev = evdev.InputDevice(path)

            if dev.info.vendor != vendor:
                continue

            if dev.info.product != product:
                continue

            caps = dev.capabilities(verbose=False)
            keys = caps.get(evdev.ecodes.EV_KEY, [])

            if evdev.ecodes.KEY_VOLUMEUP in keys or evdev.ecodes.KEY_VOLUMEDOWN in keys:
                self._consumer_device = dev
                return dev

        return None

    def __repr__(self):
        return (
            f"<PulseOutputDevice [Index: {self.index}] "
            f"Desc: {self.description} "
            f"(Name: {self.name}, Physical: {self.is_physical})>"
        )


class PulseInputDevice:
    def __init__(self, source_info):
        self.raw = source_info
        self.index = source_info.index
        self.name = source_info.name
        self.description = source_info.description

        self.is_our_virtual = "audiomeeter.device_type" in source_info.proplist

        self.is_standard_virtual = source_info.driver in [
            "module-virtual-source.c",
            "module-remap-source.c",
            "module-pipe-source.c",
        ]

        self.is_monitor = source_info.monitor_of_sink != 4294967295

        self.physical = (
            not self.is_our_virtual
            and not self.is_standard_virtual
            and not self.is_monitor
        )

    @property
    def is_physical(self) -> bool:
        return self.physical

    @property
    def is_virtual(self) -> bool:
        return self.is_our_virtual or self.is_standard_virtual or self.is_monitor

    def __repr__(self):
        return f"<PulseInputDevice [Index: {self.index}] Desc: {self.description} (Name: {self.name}, Physical: {self.is_physical})>"


class PulseAudioManager:
    def __init__(self, app_name="audiomeeter_hardware_finder"):
        self.app_name = app_name

    def get_physical_sinks(self) -> list[PulseOutputDevice]:
        with pulsectl.Pulse(self.app_name) as pulse:
            all_sinks = pulse.sink_list()
            devices = [PulseOutputDevice(sink) for sink in all_sinks]
            return [dev for dev in devices if dev.is_physical]

    def get_virtual_sinks(self) -> list[PulseOutputDevice]:
        with pulsectl.Pulse(self.app_name) as pulse:
            all_sinks = pulse.sink_list()
            devices = [PulseOutputDevice(sink) for sink in all_sinks]
            return [dev for dev in devices if dev.is_virtual]

    def get_physical_sources(self) -> list[PulseInputDevice]:
        with pulsectl.Pulse(self.app_name) as pulse:
            all_sources = pulse.source_list()
            devices = [PulseInputDevice(src) for src in all_sources]
            return [dev for dev in devices if dev.is_physical]

    def get_virtual_sources(self) -> list[PulseInputDevice]:
        with pulsectl.Pulse(self.app_name) as pulse:
            all_sources = pulse.source_list()
            devices = [PulseInputDevice(src) for src in all_sources]
            return [dev for dev in devices if dev.is_virtual]


DevicesManager = PulseAudioManager("AudiomeeterCore")


# DEBUG
async def test():
    sink = DevicesManager.get_physical_sinks()[1]
    print(sink.consumer_device)

    from evdev import ecodes

    def callback(event):
        if event.type != ecodes.EV_KEY:
            return

        if event.value != 1:
            return

        print(ecodes.KEY[event.code])

        if event.code == ecodes.KEY_VOLUMEUP:
            print("Volume Up")
            return True

        elif event.code == ecodes.KEY_VOLUMEDOWN:
            print("Volume Down")
            return True

        elif event.code == ecodes.KEY_MUTE:
            print("Mute")
            return True

    listener = ConsumerListener(sink.consumer_device)
    listener.add_callback(callback)
    listener.start()
    while True:
        await asyncio.sleep(0.1)


# debug
if __name__ == "__main__":
    import asyncio
    from consumer_listener import ConsumerListener

    asyncio.run(test())
