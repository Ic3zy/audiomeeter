import os, json, time, struct, pulsectl, math, concurrent.futures

from pulsectl import _pulsectl as c
from base import Ctx
import asyncio

DEBUG = True

class Core:
    def __init__(self, f="audiomeeter_session.json"):
        self.pulse = pulsectl.Pulse('audiomeeter-core')
        self.f = f
        self.devices = {}

    def init(self):
        if DEBUG and os.path.exists(self.f):
            self._clean()

        if os.path.exists(self.f):

            try:
                saved = json.load(open(self.f))

                if all(m in [x.index for x in self.pulse.module_list()] for m in saved.values()):
                    self.devices = saved
                    print(" [AudioMeeter] Eski oturum:", self.devices)
                    return self.devices

            except: pass

        print(" [AudioMeeter] Sanal cihaz matrisi enjekte ediliyor...")

        self.devices = {
            "input_main": self.pulse.module_load('module-null-sink', 'sink_name=audiomeeter-input sink_properties=device.description=AudioMeeter_Input_(Main)'),
            "input_aux": self.pulse.module_load('module-null-sink', 'sink_name=audiomeeter-aux-input sink_properties=device.description=AudioMeeter_AUX_Input'),
            "out_b1": self.pulse.module_load('module-virtual-source', 'source_name=audiomeeter-out-b1 source_properties=device.description=AudioMeeter_Out_B1_(Virtual_Mic)'),
            "out_b2": self.pulse.module_load('module-virtual-source', 'source_name=audiomeeter-out-b2 source_properties=device.description=AudioMeeter_Out_B2_(Virtual_Mic)'),
        }

        json.dump(self.devices, open(self.f, "w"), indent=4)

        return self.devices
    def _clean(self):
        try:
            for k, v in json.load(open(self.f)).items():
                if not v: continue
                for m in [int(x) for x in str(v).split(",")]:
                    if m in [x.index for x in self.pulse.module_list()]:
                        try: self.pulse.module_unload(m)
                        except: pass
            os.remove(self.f)
        except: pass

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
    def __init__(self,):
        self.core = Core()
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