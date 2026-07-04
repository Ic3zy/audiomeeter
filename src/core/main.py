import os, json, time, struct, pulsectl, math, concurrent.futures

from pulsectl import _pulsectl as c

from base import Ctx
import asyncio

from .cython_core.audio_core import (
    init_audio_system,
    free_audio_system,
    AudioRecorder,
    Distributor
)


DEBUG = False

class VirtualDevices:
    def __init__(self, f="audiomeeter_session.json"):
        self.pulse = pulsectl.Pulse('audiomeeter-core')
        self.f = f
        self.devices = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.active_bridges = {}

    def init(self):
        if DEBUG and os.path.exists(self.f):
            self._clean()
            
        expected_devices = {
            "input_main": ("sink", "audiomeeter-input"),
            "input_aux": ("sink", "audiomeeter-aux-input"),
            "out_b1": ("source", "audiomeeter-out-b1"),
            "out_b2": ("source", "audiomeeter-out-b2"),
        }

        existing = {}
        try:
            for key, (dev_type, name) in expected_devices.items():
                if dev_type == "sink":
                    try:
                        sink = self.pulse.get_sink_by_name(name)
                        existing[key] = sink.index
                    except pulsectl.PulseIndexError:
                        break
                else:
                    try:
                        source = self.pulse.get_source_by_name(name)
                        existing[key] = source.index
                    except pulsectl.PulseIndexError:
                        break
            
            if len(existing) == len(expected_devices):
                self.devices = existing
                return self.devices
                
        except Exception as e:
            print(f" Core error: {e}")

        if os.path.exists(self.f):
            self._clean()

        print(" [AudioMeeter] Sanal cihaz matrisi enjekte ediliyor...")

        self.devices = {
            "input_main": self.pulse.module_load('module-null-sink', 'sink_name=audiomeeter-input sink_properties=device.description=AudioMeeter_Input_(Main)'),
            "input_aux": self.pulse.module_load('module-null-sink', 'sink_name=audiomeeter-aux-input sink_properties=device.description=AudioMeeter_AUX_Input'),
            # "out_b1": self.pulse.module_load('module-virtual-source', 'source_name=audiomeeter-out-b1 source_properties=device.description=AudioMeeter_Out_B1_(Virtual_Mic)'),
            # "out_b2": self.pulse.module_load('module-virtual-source', 'source_name=audiomeeter-out-b2 source_properties=device.description=AudioMeeter_Out_B2_(Virtual_Mic)'),
        }

        json.dump(self.devices, open(self.f, "w"), indent=4)

        return self.devices

    def _clean(self):
        try:
            for k, v in json.load(open(self.f)).items():
                if not v:
                    continue
                for m in [int(x) for x in str(v).split(",")]:
                    if m in [x.index for x in self.pulse.module_list()]:
                        try:
                            self.pulse.module_unload(m)
                        except:
                            pass
            os.remove(self.f)
        except:
            pass


class AudioCore:
    def __init__(self):
        init_audio_system()
        self.distributor = Distributor()
        self.initiliaze_core_devices()
        self.save_sink_device()
    
    def initiliaze_core_devices(self):
        name_to_id = {"input_aux": "audiomeeter-aux-input.monitor", "input_main": "audiomeeter-input.monitor"}
        
        for (name, id) in name_to_id.items():
            print(f" [AudioCore] initiliaze_core_devices: {name}, {id}")
            a = self.distributor.create_listen_device(id, name)
            a.start()
        
        
    def route_audio(self, source_id, s_name):
        sink = Ctx.get(f"H_Out_{s_name}_id")

        # No except
        if sink is None:
            return

        if source_id < 4:
            # no process from mic devices.
            return

        # virtual device name
        v_d_name = "input_main" if source_id == 4 else "input_aux"

        print(f" [AudioCore] route_audio: {v_d_name} -> {s_name}")
        self.distributor.create_bridge(v_d_name, s_name)
    
    def create_sink(self, device_id, device_name):
        print(f" [AudioCore] create_sink: {device_id}, {device_name}")
        self.distributor.create_sink(device_id, device_name)


    def save_sink_device(self):
        devices = ["A1", "A2", "A3"]
        for device in devices:
            c_name = f"H_Out_{device}_id"
            Ctx.add_callback(c_name, lambda c_n=c_name, d=device: self.create_sink(Ctx[c_n], d))
            for i in range(5):
                name = f"s_{i+1}_{device}"
                Ctx.add_callback(name, lambda n=i+1, d=device: self.route_audio(n, d))

class Engine:
    def __init__(self):
        self.v_devices = VirtualDevices()
        self.v_devices.init()

        self.core = AudioCore()
    
    def on_frequency_change(self, key, frequency):
        Ctx[key] = frequency
        print(f" [Engine] Frequency: {frequency}, Key: {key}")
    