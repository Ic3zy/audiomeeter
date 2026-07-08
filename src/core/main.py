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
        self.save_sink_device()

        self.archived_routes = []
        # {"device_name": (device, ctx_dB_name)}
        self.watch_devices = {}
        self.initialize_core_devices()



    def initialize_core_devices(self):
        name_to_id = {"input_main": "audiomeeter-input.monitor", "input_aux": "audiomeeter-aux-input.monitor"}
        
        for (name, id) in name_to_id.items():
            print(f" [AudioCore] initiliaze_core_devices: {name}, {id}")
            if name == "input_main":
                a = self.distributor.create_listen_device(id, name, is_main_device=1)
            else:
                a = self.distributor.create_listen_device(id, name)

            self.add_watch_device(a, name, name)

            a.start()

    async def dB_watchdog(self):
        try:
            lasts = {}
            while True:
                for (device_name, (device, ctx_dB_name)) in self.watch_devices.items():
                    last_db = lasts.get(device_name, 0)
                    
                    db = device.get_dB()

                    if db != last_db:
                        lasts[device_name] = db
                        
                        Ctx[ctx_dB_name] = db


                await asyncio.sleep(0.2)
        except Exception as e:
            print(f"dB_watchdog error: {e}")

    def add_watch_device(self, device, device_name, ctx_dB_name):
        self.watch_devices[device_name] = (device, ctx_dB_name)
        
    def append_archived_route(self, sink_name, v_d_name, s_name):
        archived = self.get_archived_by_sink_name(sink_name)
        if archived is None:
            self.archived_routes.append((sink_name, v_d_name, s_name))
        else:
            # TODO: remove duplicated routes
            pass
    
    def get_archived_by_sink_name(self, target_sink_name):
        for (sink_name, v_d_name, s_name) in self.archived_routes:
            if sink_name == target_sink_name:
                return (sink_name, v_d_name, s_name)

        
    def route_audio(self, source_id, s_name):
        sink_name = f"H_Out_{s_name}_id"
        sink = Ctx.get(sink_name)

        is_route = Ctx.get(f"s_{source_id}_{s_name}")
        if is_route is None:
            raise ValueError(f"s_{source_id}_{s_name} is not defined.")

        # virtual device name
        if isinstance(source_id, int):
            v_d_name = "input_main" if source_id == 4 else "input_aux"

            if source_id < 4:
            # no process from mic devices.
               return
        else:
            return

        # No except
        if sink is None:
            self.append_archived_route(source_id, v_d_name, s_name)
            return

        print(f" [AudioCore] route_audio: {v_d_name} -> {s_name}")

        if is_route:
            self.distributor.create_bridge(v_d_name, s_name)
        else:
            self.distributor.remove_bridge(v_d_name, s_name)
    
    def create_sink(self, device_id, device_name, sink_name):
        archived_bridge = self.get_archived_by_sink_name(sink_name)
            
        print(f" [AudioCore] create_sink: {device_id}, {device_name}")

        sink = self.distributor.create_sink(device_id, device_name)
        ctx_name = f"s_led_{int(device_name[-1])+5}"
        self.add_watch_device(sink, device_name, ctx_name)

        if archived_bridge is not None:
            self.route_audio(archived_bridge[0], archived_bridge[2])

    def save_sink_device(self):
        devices = ["A1", "A2", "A3"]

        for device in devices:
            c_name = f"H_Out_{device}_id"
            Ctx.add_callback(c_name, lambda c_n=c_name, d=device: self.create_sink(Ctx[c_n], d, c_n))

            for i in range(5):
                name = f"s_{i+1}_{device}"
                Ctx.add_callback(name, lambda n=i+1, d=device: self.route_audio(n, d))

class Engine:
    core = None

    def __init__(self):
        self.v_devices = VirtualDevices()
        self.v_devices.init()

    async def run(self):
        print("Engine run")
        self.core = AudioCore()
        task = self.core.dB_watchdog()
        asyncio.create_task(task)

    
    def on_frequency_change(self, key, frequency):
        Ctx[key] = frequency
        print(f" [Engine] Frequency: {frequency}, Key: {key}")
    