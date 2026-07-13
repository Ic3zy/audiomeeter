# distutils: libraries = pulse
# audio_core.pyx
# cython: language_level=3

# For now, the entire engine is kept in a single .pyx file.
# I don't want to spend time dealing with build issues while the core
# architecture is still changing.
#
# I removed the old, partially working implementation and decided to
# rewrite it from scratch.
#
# TODO:
# - Decibel calculations are currently non-functional and deactivated. Fix this.
# - Implement the gain processing algorithm.
# - Implement the equalizer (bass, mid, treble) processing algorithm.

import sys
from libc.stdint cimport uint32_t, uint8_t, int16_t
from libc.stddef cimport size_t
from libc.stdlib cimport malloc, free, calloc
from libc.stdio cimport printf, fflush, stdout
from libc.math cimport log10, sqrt
from libc.string cimport memset, memcpy
from libc.stdint cimport int64_t
from libc.stdint cimport uintptr_t
from libc.string cimport strcmp, strncpy
from libc.math cimport pow

cdef extern from "<time.h>" nogil:
    ctypedef long time_t
    struct timespec:
        time_t tv_sec
        long tv_nsec

    int CLOCK_MONOTONIC
    int clock_gettime(int clk_id, timespec * tp)

cdef extern from "stdio.h" nogil:
    int snprintf(char * str, size_t size, const char * format, ...)

cdef extern from "rt_biquad/include/rt_biquad.h" nogil:
    struct rt_biquad_state:
        pass

    struct rt_band:
        pass

    rt_band* create_band(float start_hz, float end_hz, float db_gain, float sample_rate)
    
    void update_band(rt_band *band, float start_hz, float end_hz, float db_gain, float sample_rate)

    void destroy_band(rt_band *band)
    
    void filter_from_hz_list(rt_band *bands, float *samples, int length, float sample_rate, int band_count)


DEF MAX_DEVICES = 32
DEF MAX_ROUTES_PER_DEVICE = 8
DEF MAX_NAME_LEN = 32
DEF BUFFER_LEN = 2048
DEF SAMPLES_COUNT = BUFFER_LEN // 4

# TODO: implement bass, mid, treble 
cdef struct Equalizer:
    rt_band *bass_band
    rt_band *mid_band
    rt_band *treble_band

    double gain

cdef struct Buffer:
    float samples[SAMPLES_COUNT]

cdef struct Sink_Core:
    AudioCore * core
    Equalizer eq
    char device_id[128]
    int instance_id
    int dB_counter
    int dB

    int top_updateable
    int active_buffer_ids[MAX_ROUTES_PER_DEVICE]
    Buffer buffers[MAX_DEVICES]

cdef struct DeviceBridge:
    Sink_Core * target_sinks[MAX_ROUTES_PER_DEVICE]
    int active_route_count

cdef struct AudioCore:
    Equalizer eq

    Sink_Core * bridged_sinks[MAX_ROUTES_PER_DEVICE]
    int active_bridge_count

    char device_id[256]
    int instance_id
    int is_active
    int dB
    int is_main_device # only 0 or 1
    
cdef struct AudioManager:
    AudioCore * devices[MAX_DEVICES]
    Sink_Core * sinks[MAX_DEVICES]

    timespec last_tick

cdef AudioManager * manager = NULL

cdef int add_single_sink_to_bridge(int v_device_id, Sink_Core * sink) noexcept:
    if manager == NULL or sink == NULL:
        return -3
        
    if v_device_id < 0 or v_device_id >= MAX_DEVICES:
        return -3
    
    printf("v_device_id: %d\n", v_device_id)

    cdef AudioCore * current_core = manager.devices[v_device_id]
    if current_core == NULL:
        return -3
    
    cdef int count = current_core.active_bridge_count
    cdef int i
    
    for i in range(MAX_ROUTES_PER_DEVICE):
        if current_core.bridged_sinks[i] == sink:
            return -2
    
    if count < MAX_ROUTES_PER_DEVICE:
        for i in range(MAX_ROUTES_PER_DEVICE):
            if current_core.bridged_sinks[i] == NULL:
                current_core.bridged_sinks[i] = sink
                current_core.active_bridge_count += 1
                return 0
        
    return -1 

cdef int remove_single_sink_from_bridge(int v_device_id, const char* device_id) noexcept nogil:
    if manager == NULL or device_id == NULL:
        return -3
        
    if v_device_id < 0 or v_device_id >= MAX_DEVICES:
        return -3
        
    cdef AudioCore * current_core = manager.devices[v_device_id]
    if current_core == NULL:
        return -3

    cdef int i
    
    for i in range(MAX_ROUTES_PER_DEVICE):
        if current_core.bridged_sinks[i] == NULL:
            continue
            
        if strcmp(current_core.bridged_sinks[i].device_id, device_id) == 0:
            current_core.bridged_sinks[i] = NULL
            
            if current_core.active_bridge_count > 0:
                current_core.active_bridge_count -= 1
                
            printf(b"Sink '%s' removed from v_device_id: %d, slot: %d\n", device_id, v_device_id, i)
            return 0
            
    return -2

cdef void write(Sink_Core * core, const void * data, size_t length, int dB) noexcept nogil:
    if data == NULL:
        return

    if core.dB_counter >= 100:
        core.dB = dB
        core.dB_counter = 0
    else:
        core.dB_counter += 1
    
    if core == NULL:
        return
    
cdef inline double calculate_rms(float * samples, size_t num_samples) noexcept nogil:
    cdef size_t i
    cdef double sum_squares = 0.0

    for i in range(num_samples):
        sum_squares += ( < double > samples[i] * < double > samples[i])

    return sqrt(sum_squares / num_samples) if num_samples > 0 else 0.0

cdef inline int rms_to_db(double rms) noexcept nogil:
    cdef double db = -200.0

    if rms > 0.000001:
        db = 20.0 * log10(rms)

    if db > 12.0:
        return 12
    if db < -200.0:
        return -200

    return < int > db

cdef inline int calculate_db(float * samples, size_t num_samples) noexcept nogil:
    # calculate RMS 
    cdef double rms = calculate_rms(samples, num_samples)
    # convert to dB
    cdef int db = rms_to_db(rms)

    return db

cdef inline void route_audio(int src_id, float * data, size_t length) noexcept nogil:
    cdef AudioCore * current_core = manager.devices[src_id]
    cdef int db, bi
    cdef rt_band band[3]

    if current_core == NULL:
        return
    
    if current_core.active_bridge_count == 0:
        return

    if current_core.eq.gain != 1.0:
        for bi in range(SAMPLES_COUNT):
            data[bi] = <float>(data[bi] * current_core.eq.gain)


    # calculate dB of only the leading 24 samples


    db = calculate_db(<float *>data, 24)
    current_core.dB = db

    for sink in current_core.bridged_sinks:
        if sink == NULL:
            continue
        
        memcpy(<void*>sink.buffers[src_id].samples, <void*>data, BUFFER_LEN)

        band[0] = current_core.eq.bass_band[0]
        band[1] = current_core.eq.mid_band[0]
        band[2] = current_core.eq.treble_band[0]
        
        filter_from_hz_list(<rt_band *>band, <float *>sink.buffers[src_id].samples, SAMPLES_COUNT, 48000, 3)

        sink.active_buffer_ids[sink.top_updateable] = src_id
        sink.top_updateable += 1

# TODO: Refactor this block for better clarity and precision.
cdef inline void stream_play() noexcept nogil:
    cdef Sink_Core * sink
    cdef Equalizer eq
    cdef float* mixing_buffer
    cdef float* current_samples 
    cdef double rms
    cdef int db, i, j, active_id
    cdef int bi 
    cdef size_t peek_limit = <size_t>(BUFFER_LEN)

    for i in range(MAX_DEVICES):
        sink = manager.sinks[i]

        if sink == NULL or sink.top_updateable == 0:
            if sink != NULL and sink.top_updateable == 0:
                write(sink, <float *>sink.buffers[sink.active_buffer_ids[0]].samples, writeable_size, sink.dB)
                    
            continue

        eq = sink.eq
            
        active_id = sink.active_buffer_ids[0]
        mixing_buffer = <float*>sink.buffers[active_id].samples

        for j in range(1, sink.top_updateable):
            active_id = sink.active_buffer_ids[j]
            current_samples = <float*>sink.buffers[active_id].samples
            
            for bi in range(SAMPLES_COUNT):
                mixing_buffer[bi] += current_samples[bi]

        if eq.gain != 1.0: 
            for bi in range(SAMPLES_COUNT):
                mixing_buffer[bi] = <float>(mixing_buffer[bi] * eq.gain)
        
        db = calculate_db(mixing_buffer, 24)
        

        write(sink, mixing_buffer, BUFFER_LEN, db)
        
        sink.top_updateable = 0

cdef inline void core_tick() noexcept nogil:
    cdef AudioCore * current_core
    cdef const void * data
    cdef size_t peek_limit
    cdef int i

    for i in range(MAX_DEVICES):
        current_core = manager.devices[i]
        if current_core == NULL:
            continue
        
        if current_core.is_active == 0:
            continue
        
        peek_limit = <size_t>(BUFFER_LEN) 

        if data == NULL:
            continue
            
        route_audio(current_core.instance_id, <float *>data, peek_limit)

    stream_play()

cdef void initialize_bands(Equalizer *eq) noexcept nogil:
    eq.bass_band = create_band(20.0, 100.0, 0.0, 48000)
    eq.mid_band = create_band(100.0, 4000.0, 0.0, 48000)
    eq.treble_band = create_band(4000.0, 20000.0, 0.0, 48000)


cdef class AudioRecorder:
    cdef AudioCore * core

    def __cinit__(self, bytes device_id, int instance_id, int is_main_device=0):
        global manager
        if manager == NULL:
            raise RuntimeError(
                "The system must be initialized in RAM by calling 'init_audio_system()' first!"
            )

        if instance_id < 0 or instance_id >= MAX_DEVICES:
            raise ValueError(
                f"Instance ID must be between 0 and {MAX_DEVICES - 1}!"
            )

        self.core = <AudioCore *>calloc(1, sizeof(AudioCore))
        if self.core == NULL:
            raise MemoryError("Failed to allocate RAM for the device at C-level.")

        initialize_bands(&self.core.eq)

        snprintf(
            self.core.device_id,
            sizeof(
                self.core.device_id),
            "%s",
            device_id)

        manager.devices[instance_id] = self.core

    def start(self):
        manager.devices[self.core.instance_id] = self.core
                
        with nogil:
            if self.core.is_main_device:
                pass

    # TODO: replace with public cdef double
    @property
    def dB(self):
        return self.core.dB
    
    def get_dB(self):
        return self.core.dB

    cpdef get_id(self):
        return self.core.instance_id

    def stop(self):
        if self.core == NULL:
            return

    def __dealloc__(self):
        global manager
        self.stop()
        if self.core != NULL:
            if manager != NULL:
                manager.devices[self.core.instance_id] = NULL
            free(self.core)


cdef class SinkDevice:
    cdef Sink_Core* core
    def __cinit__(self, bytes device_id, int instance_id):
        self.core = <Sink_Core*>calloc(1, sizeof(Sink_Core))

        # ram safety
        if self.core == NULL:
            raise MemoryError("error: failed to allocate RAM")

        cdef char * c_device_id = device_id
        strncpy(self.core.device_id, c_device_id, 127)
        self.core.device_id[127] = b'\0'
        
        if manager == NULL:
            print("error: not initialized manager")
            return

    def get_device_id(self):
        return self.core.device_id

    def get_dB(self):
        return self.core.dB



# two key = value
cdef class BridgeManager:
    cdef public dict by_name
    cdef public dict by_id
    cdef public dict name_to_id_dict

    def __cinit__(self):
        self.by_name = {}
        self.by_id = {}
        self.name_to_id_dict = {}

    def register(self, str name, str device_id, object instance):
        self.by_name[name] = instance
        self.by_id[device_id] = instance
        self.name_to_id_dict[name] = device_id

    def get_balanced(self, object key):
        return self.by_name.get(key) or self.by_id.get(key)
    
    def get_by_name(self, str name):
        return self.by_name.get(name)
    
    def get_by_id(self, str device_id):
        return self.by_id.get(device_id)
    
    def name_to_id(self, str name):
        return self.name_to_id_dict.get(name)

    def values(self):
        return self.by_name.values()

    def unregister(self, str name, str device_id):
        self.by_name.pop(name, None)
        self.by_id.pop(device_id, None)
        self.name_to_id_dict.pop(name, None)
        

class Distributor:
    def __init__(self):
        # AudioRecorder devices
        self.devices = BridgeManager()
        # Output sink devices
        self.sinks = BridgeManager()
        self.last_instance_id = 0
        self.setted_main_device = 0

    # The device name is used as an identifier when establishing audio bridges.
    # It must be unique; no two devices can share the same name.
    # This name is not tied to any hardware spec and is defined on the Python side.
    # Unlike the device_id, it does not need to be fetched from a specific system path.
    def create_sink(self, device_id, device_name):
        cdef bytes b_device_id
        cdef SinkDevice sink
        cdef Sink_Core * sink_core
        
        try:
            if isinstance(device_id, str):
                b_device_id = device_id.encode('utf-8')
            else:
                b_device_id = device_id

            sink = SinkDevice(b_device_id, self.last_instance_id)
            
            if manager != NULL:
                sink_core = sink.core
                manager.sinks[self.last_instance_id] = sink_core
            else:
                raise RuntimeError("Manager is not initialized!")

        except Exception as e:
            print(f"create_sink error: {e}")
            import traceback
            traceback.print_exc()

            return None
        
        self.sinks.register(device_name, device_id, sink)
        self.last_instance_id += 1
        return sink
    
    def create_listen_device(self, str device_id, str device_name, int is_main_device=0):
        # convert to bytes
        listen = AudioRecorder(device_id.encode('utf-8'), self.last_instance_id, is_main_device)

        if self.setted_main_device != is_main_device:
            if not self.setted_main_device and is_main_device:
                self.setted_main_device = True

            self.devices.register(device_name, device_id, listen)
        else:
            raise ValueError("The main device can only be assigned once, and helper devices cannot be assigned before a main device.")

        self.last_instance_id += 1
            
        return listen
            

    def get_dB_by_name(self, name, sink=False):
        if sink:
            sink_obj = self.sinks.get_by_name(name)
            if sink_obj is None:
                raise ValueError(f"Sink not found: {name}")

            return sink_obj.get_dB()
        else:
            listen_obj = self.devices.get_by_name(name)
            if listen_obj is None:
                raise ValueError(f"Listen not found: {name}")
            
            return listen_obj.dB

    # device_name -> sink_name
    def create_bridge(self, str device_name, str sink_name):
        cdef SinkDevice sink_obj = self.sinks.get_by_name(sink_name)
        if sink_obj is None:
            raise ValueError(f"Sink not found: {sink_name}")
        
        listen = self.devices.get_by_name(device_name)
        if listen is None:
            raise ValueError(f"Listen not found: {device_name}")
        
        listen_id = listen.get_id()
        
        if listen_id < 0 or listen_id >= MAX_DEVICES:
            raise IndexError("Listen ID out of bounds")

        res = add_single_sink_to_bridge(listen_id, <Sink_Core *>sink_obj.core)
        
        if res == -1:
            raise OverflowError(f"Maximum route limit ({MAX_ROUTES_PER_DEVICE}) reached for this device!")
        elif res == -2:
            raise ValueError(f"Device '{sink_name}' is already routed to this bridge.")
        elif res == -3:
            raise RuntimeError("Invalid audio manager pointer or device ID.")

    def remove_bridge(self, str device_name, str sink_name):
        cdef SinkDevice sink_obj = self.sinks.get_by_name(sink_name)
        if sink_obj is None:
            raise ValueError(f"Sink not found: {sink_name}")

        cdef Sink_Core * sink_core = sink_obj.core
        if sink_core == NULL:
            raise ValueError(f"Sink core not found: {sink_name}")
        
        sink_core.dB = -200

        cdef char * device_id = sink_core.device_id

        listen = self.devices.get_by_name(device_name)
        if listen is None:
            raise ValueError(f"Listen not found: {device_name}")
        
        listen_id = listen.get_id()
        
        if listen_id < 0 or listen_id >= MAX_DEVICES:
            raise IndexError("Listen ID out of bounds")

        cdef int res = remove_single_sink_from_bridge(listen_id, device_id)
        
        if res < 0:
            raise ValueError(f"Device '{sink_name}' is not routed to this bridge.")
        
    def db_to_gain(self, double db):
        if db <= -60.0:
            return 0.0
        
        return pow(10.0, db / 20.0)

    def set_db_from_device_name(self, str device_name, double db):
        cdef AudioRecorder listen_obj = self.devices.get_by_name(device_name)
        if listen_obj is None:
            raise ValueError(f"Listen not found: {device_name}")
        
        cdef AudioCore * current_core = listen_obj.core

        if current_core == NULL:
            return
        
        cdef double gain = self.db_to_gain(db)

        current_core.eq.gain = gain

    def set_db_from_sink_name(self, str sink_name, double db):
        cdef SinkDevice sink_obj = self.sinks.get_by_name(sink_name)
        if sink_obj is None:
            raise ValueError(f"Sink not found: {sink_name}")
        
        cdef Sink_Core * sink_core = sink_obj.core
        if sink_core == NULL:
            return
        
        cdef double gain = self.db_to_gain(db)

        sink_core.eq.gain = gain

    def set_eq_from_device_name(self, str device_name, str type, float value):
        print(f"set_eq_from_device_name: {device_name}, {type}, {value}")
        cdef AudioRecorder listen_obj = self.devices.get_by_name(device_name)
        if listen_obj is None:
            raise ValueError(f"Listen not found: {device_name}")
        
        cdef AudioCore * current_core = listen_obj.core
        if current_core == NULL:
            return
        
        if type == "bass":
            update_band(current_core.eq.bass_band, 20.0, 100.0, value, 48000)
        elif type == "mid":
            update_band(current_core.eq.mid_band, 100.0, 4000.0, value, 48000)
        elif type == "treble":
            update_band(current_core.eq.treble_band, 4000.0, 20000.0, value, 48000)
        else:
            raise ValueError(f"Invalid equalizer type: {type}")

def init_audio_system():
    global manager

    cdef int i

    if manager == NULL:
        manager = <AudioManager *>calloc(1, sizeof(AudioManager))
        if manager == NULL:
            raise MemoryError("Out of memory!")

        for i in range(MAX_DEVICES):
            manager.devices[i] = NULL

def free_audio_system():
    global manager
    if manager != NULL:
        free(manager)
        manager = NULL

def run_test():
    import time
    init_audio_system()

    cdef bytes mic_device = b"alsa_output.usb-XiiSound_Technology_Corporation_Fuxi-H7-00.analog-stereo.monitor"
    cdef bytes speaker_device = b"alsa_output.usb-XiiSound_Technology_Corporation_Fuxi-H7-00.analog-stereo.monitor"

    mic_recorder = AudioRecorder(mic_device, instance_id=1)

    speaker_recorder = AudioRecorder(speaker_device, instance_id=2)

    mic_recorder.start()
    speaker_recorder.start()

    try:
        # pass
        while True:
            time.sleep(0.2)
            print(f"Mic dB: {mic_recorder.dB} | Speaker dB: {speaker_recorder.dB}")
    except KeyboardInterrupt:
        print(
            "\n\nerr.")
    finally:
        mic_recorder.stop()
        speaker_recorder.stop()
        free_audio_system()


# run_test()