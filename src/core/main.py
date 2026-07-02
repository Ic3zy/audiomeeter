import os, json, time, struct, pulsectl, math, concurrent.futures

from pulsectl import _pulsectl as c
from base import Ctx
import asyncio

DEBUG = False

class Core:
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
            "out_b1": self.pulse.module_load('module-virtual-source', 'source_name=audiomeeter-out-b1 source_properties=device.description=AudioMeeter_Out_B1_(Virtual_Mic)'),
            "out_b2": self.pulse.module_load('module-virtual-source', 'source_name=audiomeeter-out-b2 source_properties=device.description=AudioMeeter_Out_B2_(Virtual_Mic)'),
        }

        json.dump(self.devices, open(self.f, "w"), indent=4)

        # Ses patlamasını önle — yeni cihazları sessiz başlat
        self._mute_all_on_init()

        self.save_callback_state()

        return self.devices

    def _mute_all_on_init(self):
        """Başlangıçta tüm sanal cihazları sessize al — kulak patlamasını önle"""
        try:
            for key in ["input_main", "input_aux"]:
                sink = self.pulse.get_sink_by_name("audiomeeter-input" if key == "input_main" else "audiomeeter-aux-input")
                self.pulse.sink_mute(sink.index, True)  # Mute on
                # Volume'u da sıfırla
                zero_vol = pulsectl.PulseVolumeInfo(0.0, len(sink.volume.values))
                self.pulse.sink_volume_set(sink.index, zero_vol)
                print(f" [Init] {key} sessize alındı")
            
            for key in ["out_b1", "out_b2"]:
                source = self.pulse.get_source_by_name("audiomeeter-out-b1" if key == "out_b1" else "audiomeeter-out-b2")
                self.pulse.source_mute(source.index, True)
                zero_vol = pulsectl.PulseVolumeInfo(0.0, len(source.volume.values))
                self.pulse.source_volume_set(source.index, zero_vol)
                print(f" [Init] {key} sessize alındı")
                
        except Exception as e:
            print(f" [Init] Sessize alma hatası: {e}")

    def _do_route_worker(self, source_name: str, physical_device_name: str):
        args = f"source={source_name} sink={physical_device_name} latency_msec=20"
        
        with pulsectl.Pulse('audiomeeter-route-worker') as worker_pulse:
            return worker_pulse.module_load("module-loopback", args)

    async def route_virtual_to_physical_async(self, virtual_key: str, physical_device_name: str):
        bridge_key = f"{virtual_key}_to_{physical_device_name}"
        source_name = "audiomeeter-input.monitor" if virtual_key == "input_main" else "audiomeeter-aux-input.monitor"

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor, 
                self._do_route_worker, 
                source_name, 
                physical_device_name
            )
            
            self.active_bridges[bridge_key] = result
            print(f" [Core] Loopback oluşturuldu: {bridge_key} -> ID {result}")
            
        except Exception as e:
            print(f" [Core] Loopback hatası: {e}")
            raise

    def unroute_virtual_from_physical(self, virtual_key: str, physical_device_name: str):
        bridge_key = f"{virtual_key}_to_{physical_device_name}"
        
        loopback_id = self.active_bridges.get(bridge_key)
        if loopback_id is None:
            return
            
        try:
            self.pulse.module_unload(loopback_id)
            del self.active_bridges[bridge_key]
            if DEBUG:
                print(f" [Core] Loopback söküldü: {bridge_key}")

        except Exception as e:
            print(f" [Core] Loopback sökülürken hata: {e}")

    def update_state(self, key, input_number):
        hardware_output_key = "input_main" if input_number == 1 else "input_aux"
        print("update_state: ", key, hardware_output_key)

        if "A1" in key:
            out_device = Ctx.get("H_Out_A1_id")
        elif "A2" in key:
            out_device = Ctx.get("H_Out_A2_id")
        elif "A3" in key:
            out_device = Ctx.get("H_Out_A3_id")
        else:
            out_device = None
        
        if out_device is None:
            return
            
        # Önceki route'ları temizle
        for bridge_key in list(self.active_bridges.keys()):
            if hardware_output_key in bridge_key:
                old_id = self.active_bridges[bridge_key]
                try:
                    self.pulse.module_unload(old_id)
                    del self.active_bridges[bridge_key]
                except:
                    pass
        
        # Yeni route oluştur
        asyncio.create_task(
            self.route_virtual_to_physical_async(hardware_output_key, out_device)
        )

    def _do_volume_worker(self, target_sink_name: str, db_value: float):
        with pulsectl.Pulse('audiomeeter-vol-worker') as worker_pulse:
            try:
                sink = worker_pulse.get_sink_by_name(target_sink_name)
                
                if db_value <= -149.0:
                    factor = 0.0
                else:
                    factor = 10 ** (float(db_value) / 20.0)
                
                # Clamp 0-2.0 (max %200 volume)
                factor = min(factor, 2.0)
                
                # Mute'u kaldır (volume değiştirilecekse)
                if sink.mute:
                    worker_pulse.sink_mute(sink.index, False)
                
                new_vol = pulsectl.PulseVolumeInfo(factor, len(sink.volume.values))
                worker_pulse.sink_volume_set(sink.index, new_vol)
                
                return True
            except Exception as e:
                print(f" [Core Worker] Ses set hatası: {e}")
                import traceback
                traceback.print_exc()
                return False

    async def set_virtual_volume_db_async(self, virtual_key: str, db_value: float):
        target_sink_name = "audiomeeter-input" if virtual_key == "input_main" else "audiomeeter-aux-input"
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor, 
                self._do_volume_worker, 
                target_sink_name, 
                db_value
            )
            return result
        except Exception as e:
            print(f" [Core] Ses değiştirme hatası: {e}")
            return False

    def set_virtual_volume_db(self, c_i, db_value: float):
        print("DB: ", db_value)
        virtual_key = "input_main" if c_i == 1 else "input_aux"
        asyncio.create_task(
            self.set_virtual_volume_db_async(virtual_key, db_value)
        )

    def save_callback_state(self):
        callback_list = ["A1", "A2", "A3", "B1", "B2"]
        
        for i in range(2):
            # Lambda closure fix — default arg ile değeri capture et
            sl_name = f"s_sl_{i+4}"

            def make_volume_callback(idx):
                return lambda: self.set_virtual_volume_db(idx, Ctx.get(f"s_sl_{idx+4}"))
            
            Ctx.add_callback(sl_name, make_volume_callback(i))
            
            for callback in callback_list:
                name = f"s_{i+4}_{callback}"
                
                def make_route_callback(n, current_i):
                    return lambda: self.update_state(n, current_i + 1)
                
                Ctx.add_callback(name, make_route_callback(name, i))

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

class Watcher:
    def __init__(self, core, callback):
        self.pulse = core.pulse
        self.last_peak = {}
        self._streams = {}
        self._peak_vals = {}
        self._cb_wrappers = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.callback = callback

    def _make_stream(self, monitor_name):
        ss = c.PA_SAMPLE_SPEC(format=c.PA_SAMPLE_FLOAT32NE, rate=25, channels=1)
        proplist = c.pa.proplist_from_string(b'application.id=org.PulseAudio.pavucontrol')
        stream = c.pa.stream_new_with_proplist(self.pulse._ctx, b'peak-detect', c.byref(ss), None, proplist)
        c.pa.proplist_free(proplist)
        peak_ref = [0.0]

        def read_cb(s, nbytes, userdata):
            buff, bs = c.c_void_p(), c.c_int(nbytes)
            c.pa.stream_peek(s, c.byref(buff), c.byref(bs))
            try:
                if buff and bs.value >= 4:
                    count = bs.value // 4
                    floats = struct.unpack(f"{count}f", c.string_at(buff, bs.value))
                    peak_ref[0] = max(peak_ref[0], max(floats))
            finally:
                if bs.value: 
                    c.pa.stream_drop(s)

        cb = c.PA_STREAM_REQUEST_CB_T(read_cb)
        c.pa.stream_set_read_callback(stream, cb, None)

        flags = c.PA_STREAM_PEAK_DETECT | c.PA_STREAM_DONT_MOVE | c.PA_STREAM_ADJUST_LATENCY | c.PA_STREAM_DONT_INHIBIT_AUTO_SUSPEND
        buf_attr = c.PA_BUFFER_ATTR(fragsize=4, maxlength=2**32-1)

        c.pa.stream_connect_record(stream, monitor_name.encode('utf-8'), c.byref(buf_attr), flags)

        return stream, peak_ref, cb
    
    def _poll_stream(self, key, monitor_name):
        if key not in self._streams:
            try:
                self._streams[key], self._peak_vals[key], self._cb_wrappers[key] = self._make_stream(monitor_name)
            except Exception:
                return None
        
        self.pulse._pulse_poll(timeout=0.05)
        peak = self._peak_vals[key][0]
        self._peak_vals[key][0] = 0.0
        return peak

    def peak_to_db(self, peak, min_db=-60.0, max_db=12.0):
        if peak <= 0.000001:
            return min_db
        db = 20 * math.log10(peak)
        return max(min_db, min(max_db, db))

    def run(self):
        asyncio.run(self.run_with_async())

    async def run_with_async(self):
        monitors = [("input_main", "audiomeeter-input.monitor"), ("input_aux", "audiomeeter-aux-input.monitor")]
        last = {}
        try:
            while True:
                for key, mon in monitors:
                    if key not in last:
                        last[key] = -999
                    
                    peak = await asyncio.get_event_loop().run_in_executor(
                        self._executor, self._poll_stream, key, mon
                    )
                    if peak is None: 
                        continue
                    if peak == last[key]:
                        continue

                    print(f" [{key}] peak={peak:.4f} |")
                    last[key] = peak

                    db = self.peak_to_db(peak, min_db=-150.0, max_db=12.0)
                    self.callback(key, db)

                await asyncio.sleep(0.02)
                
        finally:
            for key, stream in self._streams.items():
                try: 
                    c.pa.stream_disconnect(stream)
                except: 
                    pass
                try: 
                    c.pa.stream_unref(stream)
                except: 
                    pass

class Engine:
    def __init__(self):
        self.core = Core()
        self.core.init()
        self.watcher = Watcher(self.core, self.on_frequency_change)
    
    def on_frequency_change(self, key, frequency):
        Ctx[key] = frequency
        print(f" [Engine] Frequency: {frequency}, Key: {key}")
    
    async def run(self):
        print("\n [Engine] Ses gücü izleme başlatıldı. Ctrl+C ile durdur.\n")
        try:
            await self.watcher.run_with_async()
        except Exception as e:
            print(f" [Engine] Ses gücü izleme başlatılırken hata oluştu: {e}")