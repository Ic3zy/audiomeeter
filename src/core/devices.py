import pulsectl


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
            "module-combine-sink.c"
        ]
        
        self.physical = not self.is_our_virtual and not self.is_standard_virtual

    @property
    def is_physical(self) -> bool:
        return self.physical

    @property
    def is_virtual(self) -> bool:
        return self.is_our_virtual or self.is_standard_virtual

    def __repr__(self):
        return f"<PulseOutputDevice [Index: {self.index}] Desc: {self.description} (Name: {self.name}, Physical: {self.is_physical})>"


class PulseAudioManager:
    def __init__(self, app_name="hardware_finder"):
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


DevicesManager = PulseAudioManager("AudiomeeterCore")