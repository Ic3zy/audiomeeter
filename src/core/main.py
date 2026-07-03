import os, json, time, struct, pulsectl, math, concurrent.futures

from pulsectl import _pulsectl as c
from base import Ctx
import asyncio

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
                # Ses patlamasını önle — başlangıçta volume sıfır
                self._mute_all_on_init()
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

class Engine:
    def __init__(self):
        self.core = VirtualDevices()
        self.core.init()
    
    def on_frequency_change(self, key, frequency):
        Ctx[key] = frequency
        print(f" [Engine] Frequency: {frequency}, Key: {key}")
    