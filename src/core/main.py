import os, json, time, struct, pulsectl, math, concurrent.futures

from evdev import ecodes
from pulsectl import _pulsectl as c

from base import Ctx
import asyncio
from . import engine
from .consumer_listener import ConsumerListener
from .devices import sink_name_to_consumer_device

DEBUG = True


def db_to_percent(db: float) -> float:
    db = max(-60.0, min(12.0, db))
    return ((db + 60.0) / 72.0) * 150.0


def percent_to_db(percent: float) -> float:
    percent = max(0.0, min(150.0, percent))
    return (percent / 150.0) * 72.0 - 60.0


class VirtualDevices:
    def __init__(self, f="audiomeeter_session.json"):
        self.pulse = pulsectl.Pulse("audiomeeter-core")
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
            "input_main": self.pulse.module_load(
                "module-null-sink",
                'sink_name=audiomeeter-input sink_properties="device.description=AudioMeeter_Input_(Main) audiomeeter.device_type=virtual"',
            ),
            "input_aux": self.pulse.module_load(
                "module-null-sink",
                'sink_name=audiomeeter-aux-input sink_properties="device.description=AudioMeeter_AUX_Input audiomeeter.device_type=virtual"',
            ),
            "out_b1": self.pulse.module_load(
                "module-null-sink",
                'sink_name=audiomeeter-out-b1 media.class=Audio/Source/Virtual sink_properties="device.description=AudioMeeter_Out_B1_(Virtual_Mic) audiomeeter.device_type=virtual"',
            ),
            "out_b2": self.pulse.module_load(
                "module-null-sink",
                'sink_name=audiomeeter-out-b2 media.class=Audio/Source/Virtual sink_properties="device.description=AudioMeeter_Out_B2_(Virtual_Mic) audiomeeter.device_type=virtual"',
            ),
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
        engine.init()
        self.archived_routes = []
        self.watch_devices = {}

        self.sinks = {}
        self.devices = {}

        self.consumer_listeners = {}

        self.muted_devices = []

        self.save_sink_device()
        self.save_source_device()
        self.initialize_core_devices()
        self.initialize_default_sinks()

    def set_eq_from_device_name(self, device_name, eq_type, db):
        if device_name not in self.devices:
            return

        device = self.devices.get(device_name)
        if device is None:
            return

        if eq_type == "bass":
            device.set_bass_gain(db)
        elif eq_type == "mid":
            device.set_mid_gain(db)
        elif eq_type == "treble":
            device.set_treble_gain(db)
        elif eq_type == "mono":
            db = bool(db)
            device.set_mono(db)
        elif eq_type == "mute":
            db = bool(db)
            if db:
                self.remove_all_routes_from_device(device_name)
            else:
                self.apply_all_routes_from_device(device_name)

    def save_eq_callback(self, name, sl_number):
        for eq_type in ["Bass", "Mid", "Treble", "Mono", "Mute"]:
            ctx_name = f"s_{sl_number}_{eq_type}"
            Ctx.add_callback(
                ctx_name,
                lambda n=name, cn=ctx_name, e=eq_type.lower(): self.set_eq_from_device_name(
                    n, e, Ctx[cn] / 7
                ),
            )

    def initialize_default_sinks(self):
        print(" [AudioCore] Scheduling default virtual sinks B1 and B2...")
        loop = asyncio.get_event_loop()
        # Delay sink creation to give PipeWire time to register
        # the virtual source node ports (input_FL/input_FR)
        loop.call_later(
            0.5, lambda: self.create_sink("audiomeeter-out-b1", "B1", "H_Out_B1_id")
        )
        loop.call_later(
            1.0, lambda: self.create_sink("audiomeeter-out-b2", "B2", "H_Out_B2_id")
        )

    def initialize_core_devices(self):
        # We strip the '.monitor' suffix because in PipeWire the node name is just the sink name
        name_to_id = {
            "input_main": "audiomeeter-input",
            "input_aux": "audiomeeter-aux-input",
        }

        for name, id in name_to_id.items():
            print(f" [AudioCore] initialize_core_devices: {name}, {id}")
            dev = engine.Device(id)
            self.devices[name] = dev

            # Allow PipeWire loop to register the ports before linking
            loop = asyncio.get_event_loop()
            loop.call_later(0.1, dev.link)

            ids = 4 if name == "input_main" else 5
            self.save_eq_callback(name, ids)
            Ctx.add_callback(
                f"s_sl_{ids}", lambda n=name, i=ids: self.set_db(n, i, is_sink=False)
            )

            self.add_watch_device(dev, name, name)

    async def dB_watchdog(self):
        try:
            lasts = {}
            while True:
                for device_name, (device, ctx_dB_name) in list(
                    self.watch_devices.items()
                ):
                    last_db = lasts.get(device_name, None)

                    try:
                        db = device.dB
                    except Exception:
                        continue

                    if last_db is None or db != last_db:
                        lasts[device_name] = db
                        Ctx[ctx_dB_name] = db

                await asyncio.sleep(0.03)
        except Exception as e:
            print(f"dB_watchdog error: {e}")

    def add_watch_device(self, device, device_name, ctx_dB_name):
        self.watch_devices[device_name] = (device, ctx_dB_name)

    def append_archived_route(self, sink_name, v_d_name, s_name):
        archived = self.get_archived_by_sink_name(sink_name)
        if archived is None:
            self.archived_routes.append((sink_name, v_d_name, s_name))

    def remove_archived_route(self, sink_name, v_d_name, s_name):
        archived = self.get_archived_by_sink_name(sink_name)
        if archived is None:
            return

        for i in range(len(self.archived_routes)):
            if self.archived_routes[i] == (sink_name, v_d_name, s_name):
                del self.archived_routes[i]
                return

    def get_archived_by_sink_name(self, target_sink_name):
        for sink_name, source_id, s_name in self.archived_routes:
            if sink_name == target_sink_name:
                return (source_id, s_name)
        return None

    def remove_all_routes_from_device(self, device_name):
        if device_name in self.muted_devices:
            return

        self.muted_devices.append(device_name)

        for sink_name, source_id, s_name in self.archived_routes:
            if sink_name == device_name:
                device_obj = self.devices.get(device_name)
                if device_obj:
                    sink_obj = self.sinks.get(source_id)
                    if sink_obj:
                        device_obj.unbridge(sink_obj)
                    else:
                        print(
                            f" [AudioCore] remove_all_routes_from_device: invalid source_id: {source_id}"
                        )

    def apply_all_routes_from_device(self, device_name):
        print(f" [AudioCore] apply_all_routes_from_device: {device_name}")
        if device_name not in self.muted_devices:
            return

        self.muted_devices.remove(device_name)

        for sink_name, source_id, s_name in self.archived_routes:
            if sink_name == device_name:
                print(
                    f" [AudioCore] apply_all_routes_from_device: sink_name: {sink_name}"
                )
                device_obj = self.devices.get(device_name)
                if device_obj:
                    sink_obj = self.sinks.get(source_id)
                    if sink_obj:
                        print(
                            f" [AudioCore] apply_all_routes_from_device: bridge {sink_name} -> {source_id}"
                        )
                        device_obj.bridge(sink_obj)
                    else:
                        print(
                            f" [AudioCore] apply_all_routes_from_device: invalid sink_name: {sink_name}"
                        )

    def route_audio(self, source_id, s_name):
        print(f" [AudioCore] route_audio: {source_id}, {s_name}")

        is_route = Ctx.get(f"s_{source_id}_{s_name}")
        if is_route is None:
            return

        id_to_name = {
            1: "in_1",
            2: "in_2",
            3: "in_3",
            4: "input_main",
            5: "input_aux",
        }

        if isinstance(source_id, int):
            v_d_name = id_to_name.get(source_id)
            if v_d_name is None:
                print(f" [AudioCore] route_audio: invalid source_id: {source_id}")
                return
        else:
            return

        device_obj = self.devices.get(v_d_name)
        sink_obj = self.sinks.get(s_name)

        print(
            f" [AudioCore] route_audio AAA: {v_d_name} -> {s_name} (active: {is_route}), {sink_obj}"
        )

        if is_route:
            if device_obj and sink_obj:
                try:
                    self.append_archived_route(v_d_name, s_name, None)
                    device_obj.bridge(sink_obj)
                except Exception as e:
                    print(f" [AudioCore] route_audio bridge error: {e}")
        else:
            if device_obj and sink_obj:
                try:
                    self.remove_archived_route(v_d_name, s_name, None)
                    if v_d_name not in self.muted_devices:
                        device_obj.unbridge(sink_obj)
                    else:
                        self.muted_devices.remove(v_d_name)

                except Exception as e:
                    print(f" [AudioCore] route_audio unbridge error: {e}")

    def create_source(self, device_id, device_name, source_name):
        print(f" [AudioCore] create_source: {device_id}, {device_name}, {source_name}")
        device_key = f"in_{device_name}"

        if device_key in self.devices:
            old_dev = self.devices.pop(device_key)
            if device_key in self.watch_devices:
                del self.watch_devices[device_key]
            old_dev.delete()

        if not device_id:
            return

        dev = engine.Device(device_id)
        self.devices[device_key] = dev

        loop = asyncio.get_event_loop()
        loop.call_later(0.1, dev.link)

        ctx_name = f"s_led_{device_name}"
        self.add_watch_device(dev, device_key, ctx_name)

        for sink_name in ["A1", "A2", "A3", "B1", "B2"]:
            if Ctx.get(f"s_{device_name}_{sink_name}"):
                self.route_audio(int(device_name), sink_name)

    def device_set_gain_from_listener(self, sink_name, slider_name, up=True):
        sink = self.sinks.get(sink_name)
        if sink is None:
            return

        ex_db = Ctx.get(slider_name)
        if ex_db is None:
            return

        ex_percent = db_to_percent(ex_db)
        ex_percent = max(0.0, min(150.0, ex_percent + (5.0 if up else -5.0)))

        db = percent_to_db(ex_percent)

        sink.set_gain_from_db(db)
        Ctx[slider_name] = db

    def listener_callback(self, event, sink_name, slider_name):
        if event.type != ecodes.EV_KEY:
            return

        if event.value != 1:
            return

        if event.code == ecodes.KEY_VOLUMEUP:
            print("Volume Up")
            self.device_set_gain_from_listener(sink_name, slider_name, up=True)
            return True

        elif event.code == ecodes.KEY_VOLUMEDOWN:
            print("Volume Down")
            self.device_set_gain_from_listener(sink_name, slider_name, up=False)
            return True

        elif event.code == ecodes.KEY_MUTE:
            # TODO: implement mute
            return True

    def create_sink(self, device_id, device_name, sink_name):
        device_name = str(device_name)
        print(f" [AudioCore] create_sink: {device_id}, {device_name}, {sink_name}")

        listener = self.consumer_listeners.get(device_name)
        if listener is not None:
            del self.consumer_listeners[device_name]

        listener = None
        consumer = sink_name_to_consumer_device(device_id)
        if consumer is None:
            print(f" [AudioCore] create_sink: invalid consumer device: {sink_name}")
        else:
            listener = ConsumerListener(consumer)
            if device_name.startswith("B"):
                s_ctx_name = f"s_sl_{int(device_name[-1])+8}"
            else:
                s_ctx_name = f"s_sl_{int(device_name[-1])+5}"

            listener.add_callback(
                lambda e: self.listener_callback(e, device_name, s_ctx_name)
            )

            listener.start()

        self.consumer_listeners[device_name] = listener

        if not device_id:
            if device_name in self.sinks:
                old_sink = self.sinks.pop(device_name)
                if device_name in self.watch_devices:
                    del self.watch_devices[device_name]
                old_sink.delete()
            return

        # Safely delete existing sink if it exists
        if device_name in self.sinks:
            old_sink = self.sinks[device_name]
            if device_name in self.watch_devices:
                del self.watch_devices[device_name]
            old_sink.delete()

        sink = engine.Sink(device_name, device_id)
        self.sinks[device_name] = sink

        # A1=6, A2=7, A3=8, B1=9, B2=10
        if device_name.startswith("B"):
            ctx_name = f"s_led_{int(device_name[-1])+8}"
        else:
            ctx_name = f"s_led_{int(device_name[-1])+5}"

        self.add_watch_device(sink, device_name, ctx_name)

        # Re-evaluate all active route flags from Ctx (s_1_A1 .. s_5_A1) for this sink
        for i in range(1, 6):
            if Ctx.get(f"s_{i}_{device_name}"):
                self.route_audio(i, device_name)

    def set_db(self, device_name, device_id, is_sink=True):
        db = Ctx.get(f"s_sl_{device_id}")
        if db is None:
            return

        obj = None

        if is_sink:
            obj = self.sinks.get(device_name)
        else:
            obj = self.devices.get(device_name)

        if obj is not None:
            obj.set_gain_from_db(db)

    def save_sink_device(self):
        devices = ["A1", "A2", "A3", "B1", "B2"]

        for device in devices:
            c_name = f"H_Out_{device}_id"
            # A1=6, A2=7, A3=8, B1=9, B2=10
            if device.startswith("B"):
                ids = int(device[-1]) + 8
            else:
                ids = int(device[-1]) + 5
            sl_name = f"s_sl_{ids}"

            # B1/B2 are fixed virtual mic sinks managed by initialize_default_sinks,
            # don't register a device-swap callback for them.
            if not device.startswith("B"):
                Ctx.add_callback(
                    c_name,
                    lambda c_n=c_name, d=device: self.create_sink(Ctx[c_n], d, c_n),
                )

            for i in range(5):
                name = f"s_{i+1}_{device}"
                Ctx.add_callback(name, lambda n=i + 1, d=device: self.route_audio(n, d))

            Ctx.add_callback(sl_name, lambda n=device, i=ids: self.set_db(n, i))

    def save_source_device(self):
        #              1,2,3
        for device in range(1, 4):
            ctx_name = f"H_In_{device}"
            Ctx.add_callback(
                ctx_name,
                lambda c_n=ctx_name, d=device: self.create_source(Ctx[c_n], d, c_n),
            )

            for i in range(5):
                name = f"s_{i+1}_{device}"
                Ctx.add_callback(name, lambda n=i + 1, d=device: self.route_audio(n, d))

            Ctx.add_callback(
                f"s_sl_{device}",
                lambda n=device: self.set_db(f"in_{n}", n, is_sink=False),
            )


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
