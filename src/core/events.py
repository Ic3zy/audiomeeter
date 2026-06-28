import os
import json
import time
import struct
import pulsectl
from pulsectl import _pulsectl as c

DEBUG = True


class AudioMeeterCoreManager:
    def __init__(self, session_file="audiomeeter_session.json"):
        self.pulse = pulsectl.Pulse('audiomeeter-core')
        self.session_file = session_file
        self.devices = {}

    def initialize_audio_matrix(self):
        if DEBUG and os.path.exists(self.session_file):
            print(" debug modu aktif eski cihazlar temizleniyor")
            self._cleanup_previous_session()

        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r") as f:
                    saved_modules = json.load(f)
                
                current_modules = [m.index for m in self.pulse.module_list()]
                if all(mod_id in current_modules for mod_id in saved_modules.values()):
                    self.devices = saved_modules
                    print("eski oturum cihazları başarıyla bağlandı:", self.devices)
                    return self.devices
            except Exception:
                print("oturum dosyası geçersiz veya cihazlar uçmuş, yeniden oluşturuluyor")

        print("sanal cihaz matrisi PipeWire/PulseAudio üzerine enjekte ediliyor")
        self.devices = {}

        self.devices["input_main"] = self._create_sink("audiomeeter-input", "AudioMeeter Input (Main)")
        self.devices["input_aux"] = self._create_sink("audiomeeter-aux-input", "AudioMeeter AUX Input")
        self.devices["out_b1"] = self._create_virtual_microphone("audiomeeter-out-b1", "AudioMeeter Out B1 (Virtual Mic)")
        self.devices["out_b2"] = self._create_virtual_microphone("audiomeeter-out-b2", "AudioMeeter Out B2 (Virtual Mic)")

        with open(self.session_file, "w") as f:
            json.dump(self.devices, f, indent=4)

        return self.devices

    def _create_sink(self, name, label):
        safe_label = label.replace(" ", "_")
        module_args = f"sink_name={name} sink_properties=device.description={safe_label}"
        try:
            return self.pulse.module_load('module-null-sink', module_args)
        except Exception as e:
            print(f"sink oluşturulurken hata ({name}): {e}")
            return None

    def _create_virtual_microphone(self, name, label):
        safe_label = label.replace(" ", "_")
        module_args = f"source_name={name} source_properties=device.description={safe_label}"
        try:
            return self.pulse.module_load('module-virtual-source', module_args)
        except Exception as e:
            print(f"mikrofon oluşturulurken hata ({name}): {e}")
            return None

    def _cleanup_previous_session(self):
        try:
            with open(self.session_file, "r") as f:
                saved_modules = json.load(f)
            current_modules = [m.index for m in self.pulse.module_list()]
            for key, val in saved_modules.items():
                if not val: 
                    continue
                mod_ids = [int(x) for x in str(val).split(",")]
                for mod_id in mod_ids:
                    if mod_id in current_modules:
                        try: 
                            self.pulse.module_unload(mod_id)
                            print(f"modül ID {mod_id} kaldırıldı.")
                        except Exception: 
                            pass
            os.remove(self.session_file)
        except Exception as e:
            print(f" temizlik hatası: {e}")


class AudioMeeterEngineDirectPulse:
    def __init__(self, core_manager):
        self.core = core_manager
        self.pulse = core_manager.pulse
        self._stream = None
        self._peak_value = 0.0

    def _stream_read_cb(self, s, nbytes, userdata):
        buff = c.c_void_p()
        bs = c.c_int(nbytes)
        
        c.pa.stream_peek(s, c.byref(buff), c.byref(bs))
        
        try:
            if buff and bs.value >= 4:
                count = bs.value // 4
                floats = struct.unpack(f"{count}f", c.string_at(buff, bs.value))
                self._peak_value = max(self._peak_value, max(floats))
        finally:
            if bs.value > 0:
                c.pa.stream_drop(s)

    def start_monitoring_loop(self, target_sink_name="audiomeeter-input"):
        monitor_source_name = f"{target_sink_name}.monitor"
        print(f"\n {monitor_source_name}' için canlı sinyal takibi başlatılıyor")

        try:
            source = self.pulse.get_source_by_name(monitor_source_name)
            print(f"monitor source bulundu: {source.name} (index: {source.index})")
        except pulsectl.PulseIndexError:
            print(f"hata '{monitor_source_name}' monitor source bulunamadı!")
            return

        ss = c.PA_SAMPLE_SPEC(format=c.PA_SAMPLE_FLOAT32NE, rate=25, channels=1)
        proplist = c.pa.proplist_from_string('application.id=org.PulseAudio.pavucontrol')
        
        self._stream = c.pa.stream_new_with_proplist(
            self.pulse._ctx, 
            b'audiomeeter-peak-meter', 
            c.byref(ss), 
            None, 
            proplist
        )
        c.pa.proplist_free(proplist)

        self._read_cb_wrapper = c.PA_STREAM_REQUEST_CB_T(self._stream_read_cb)
        c.pa.stream_set_read_callback(self._stream, self._read_cb_wrapper, None)

        flags = (c.PA_STREAM_PEAK_DETECT | 
                 c.PA_STREAM_DONT_MOVE | 
                 c.PA_STREAM_ADJUST_LATENCY |
                 c.PA_STREAM_DONT_INHIBIT_AUTO_SUSPEND)

        buf_attr = c.PA_BUFFER_ATTR(fragsize=4, maxlength=2**32-1)

        try:
            c.pa.stream_connect_record(
                self._stream,
                monitor_source_name.encode('utf-8'),
                c.byref(buf_attr),
                flags
            )
        except c.pa.CallError as e:
            print(f" [Hata] Stream bağlanamadı: {e}")
            c.pa.stream_unref(self._stream)
            self._stream = None
            return

        print("sinyal gücü okunuyor\n")

        try:
            while True:
                self.pulse._pulse_poll(timeout=0.05)
                
                peak_signal = self._peak_value
                self._peak_value = 0.0 
                
                if peak_signal > 0.005:
                    print(f" [ACTIVE] : {peak_signal:.4f}", end="\r", flush=True)
                else:
                    print(f" [SILENT] : {peak_signal:.4f}", end="\r", flush=True)
                
        except Exception as e:
            print(f"\n izleme sırasında hata: {e}")
        finally:
            self._cleanup_stream()

    def _cleanup_stream(self):
        if self._stream:
            try:
                c.pa.stream_disconnect(self._stream)
            except Exception:
                pass
            try:
                c.pa.stream_unref(self._stream)
            except Exception:
                pass
            self._stream = None


if __name__ == "__main__":
    core = AudioMeeterCoreManager()
    core.initialize_audio_matrix()
    
    engine = AudioMeeterEngineDirectPulse(core)
    engine.start_monitoring_loop("audiomeeter-input")