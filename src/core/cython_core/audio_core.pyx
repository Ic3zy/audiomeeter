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

cdef extern from "pulse/pulseaudio.h" nogil:
    ctypedef struct pa_sample_spec:
        int format
        uint32_t rate
        uint8_t channels

    ctypedef struct pa_buffer_attr:
        uint32_t maxlength, tlength, prebuf, minreq, fragsize

    ctypedef struct pa_threaded_mainloop
    ctypedef struct pa_mainloop_api
    ctypedef struct pa_context
    ctypedef struct pa_stream

    pa_threaded_mainloop * pa_threaded_mainloop_new()
    pa_mainloop_api * pa_threaded_mainloop_get_api(pa_threaded_mainloop *)
    int pa_threaded_mainloop_start(pa_threaded_mainloop *)
    void pa_threaded_mainloop_stop(pa_threaded_mainloop *)
    void pa_threaded_mainloop_free(pa_threaded_mainloop *)

    pa_context * pa_context_new(pa_mainloop_api *, const char*)
    int pa_context_connect(pa_context * , const char*, int, void*)
    void pa_context_disconnect(pa_context * )
    void pa_context_unref(pa_context * )
    int pa_context_get_state(pa_context * )
    int pa_context_errno(pa_context * )
    const char * pa_strerror(int)
    void pa_context_set_state_callback(pa_context *, void(*)(pa_context*, void*) noexcept nogil, void*)

    pa_stream * pa_stream_new(pa_context *, const char*, pa_sample_spec*, void*)
    void pa_stream_unref(pa_stream * )
    int pa_stream_connect_record(pa_stream * , const char*, pa_buffer_attr*, int)
    int pa_stream_disconnect(pa_stream * )
    void pa_stream_set_read_callback(pa_stream * , void(*)(pa_stream*, size_t, void*) noexcept nogil, void*)
    void pa_stream_set_write_callback(
        pa_stream *p, 
        void (*cb)(pa_stream *p, size_t nbytes, void *userdata), 
        void *userdata
    )

    int pa_stream_peek(pa_stream * , const void**, size_t*)
    int pa_stream_drop(pa_stream * )
    int pa_stream_get_state(pa_stream * )
    int pa_stream_connect_playback(pa_stream * s, const char * dev, pa_buffer_attr * attr, int flags, const void * volume, pa_stream * sync_stream)
    size_t pa_stream_readable_size(pa_stream* s) nogil

    int pa_stream_begin_write(pa_stream* s, void** data, size_t* nbytes) noexcept nogil
    int pa_stream_write(pa_stream* s, const void* data, size_t nbytes, void (*free_cb)(void*), int64_t offset, int seek) noexcept nogil

    ctypedef struct pa_mainloop
    pa_mainloop * pa_mainloop_new()
    pa_mainloop_api * pa_mainloop_get_api(pa_mainloop *)
    int pa_mainloop_iterate(pa_mainloop *, int block, int * retval)
    void pa_mainloop_free(pa_mainloop *)
    const char* pa_stream_get_device_name(const pa_stream* s)

cdef extern from "pulse/sample.h":
    cdef int PA_SAMPLE_S16LE
    cdef int PA_SAMPLE_FLOAT32LE

cdef extern from "pulse/def.h":
    cdef enum pa_seek_mode:
        PA_SEEK_RELATIVE

cdef int PA_CONTEXT_READY = 4
cdef int PA_STREAM_READY = 2

DEF MAX_DEVICES = 32
DEF MAX_ROUTES_PER_DEVICE = 8
DEF MAX_NAME_LEN = 32
DEF BUFFER_LEN = 2048
DEF SAMPLES_COUNT = BUFFER_LEN // 4

# sse4.2 requires 16 byte alignment
DEF ALIGNED_SAMPLES_COUNT = SAMPLES_COUNT + 4

# TODO: implement bass, mid, treble 
cdef struct Equalizer:
    double gain

cdef struct Buffer:
    float samples[ALIGNED_SAMPLES_COUNT]

cdef struct Sink_Core:
    AudioCore * core
    pa_stream * stream
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
    pa_threaded_mainloop * mainloop
    pa_mainloop_api * mainloop_api
    pa_context * context
    pa_stream * stream
    pa_sample_spec ss

    Equalizer eq

    Sink_Core * bridged_sinks[MAX_ROUTES_PER_DEVICE]
    int active_bridge_count

    char device_id[256]
    int instance_id
    int is_active
    int dB
    int is_main_device # only 0 or 1
    
cdef struct AudioManager:
    pa_threaded_mainloop * mainloop
    pa_context * context
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

    if current_core == NULL:
        return
    
    if current_core.active_bridge_count == 0:
        return

    if current_core.eq.gain != 1.0:
        for bi in range(ALIGNED_SAMPLES_COUNT):
            data[bi] = <float>(data[bi] * current_core.eq.gain)

    # calculate dB of only the leading 24 samples
    db = calculate_db(<float *>data, 24)
    current_core.dB = db

    for sink in current_core.bridged_sinks:
        if sink == NULL:
            continue
        
        memcpy(<void*>sink.buffers[src_id].samples, <void*>data, BUFFER_LEN)
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
            continue

        eq = sink.eq
            
        active_id = sink.active_buffer_ids[0]
        mixing_buffer = <float*>sink.buffers[active_id].samples

        for j in range(1, sink.top_updateable):
            active_id = sink.active_buffer_ids[j]
            current_samples = <float*>sink.buffers[active_id].samples
            
            for bi in range(ALIGNED_SAMPLES_COUNT):
                mixing_buffer[bi] += current_samples[bi]

        if eq.gain != 1.0: 
            for bi in range(ALIGNED_SAMPLES_COUNT):
                mixing_buffer[bi] = <float>(mixing_buffer[bi] * eq.gain)
        
        db = calculate_db(mixing_buffer, 24)
        
        write(sink, mixing_buffer, peek_limit, db)
        
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
        
        if pa_stream_peek(current_core.stream, &data, &peek_limit) < 0:
            continue

        if data == NULL:
            continue
            
        route_audio(current_core.instance_id, <float *>data, peek_limit)
        pa_stream_drop(current_core.stream)

    stream_play()

# Main audio read callback:
# This callback is executed only by the device specified as the main device.
# Using a single device as the read source avoids clock drift as well as
# buffer underrun/overrun synchronization issues.
# This approach is significantly more stable.
cdef void stream_read_callback(pa_stream * stream, size_t length, void * userdata) noexcept nogil:
    core_tick()

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

        self.core.mainloop = NULL
        self.core.context = NULL
        self.core.stream = NULL
        self.core.ss.format = PA_SAMPLE_FLOAT32LE;
        self.core.ss.rate = 48000
        self.core.ss.channels = 2
        self.core.instance_id = instance_id
        self.core.is_active = 1
        self.core.is_main_device = is_main_device
        self.core.eq.gain = 1.0

        snprintf(
            self.core.device_id,
            sizeof(
                self.core.device_id),
            "%s",
            device_id)

        manager.devices[instance_id] = self.core

    def start(self):
        manager.devices[self.core.instance_id] = self.core
        cdef int stream_flags = 0x0200 | 0x2000  # 0x0200 = DONT_MOVE, 0x2000 = ADJUST_LATENCY

        cdef pa_buffer_attr * attr = NULL
        cdef int result = 0
        cdef uint32_t target_fragment = 512 * sizeof(float) # 512 Byte
                
        with nogil:
            self.core.stream = pa_stream_new(manager.context, b"RecordStream", & self.core.ss, NULL)

            # Do not set the read callback from the auxiliary device.
            if self.core.is_main_device:
                pa_stream_set_read_callback(self.core.stream, stream_read_callback, < void * >self.core)

            attr = <pa_buffer_attr * >malloc(sizeof(pa_buffer_attr))
            if attr != NULL:
                memset(attr, 0, sizeof(pa_buffer_attr))

                attr.fragsize = target_fragment
                attr.minreq = target_fragment
                attr.tlength = target_fragment
                attr.prebuf = target_fragment
                attr.maxlength = target_fragment

            result = pa_stream_connect_record(
                self.core.stream,
                self.core.device_id,
                attr,
                stream_flags)

            if result < 0:
                printf("Hata Record baglantisi basarisiz")
                if attr != NULL:
                    free(attr)


            # if attr != NULL:
            #     free(attr)
            
    
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

        with nogil:
            self.core.is_active = 0
            if self.core.mainloop:
                pa_threaded_mainloop_stop(self.core.mainloop)
            if self.core.stream:
                pa_stream_disconnect(self.core.stream)
                pa_stream_unref(self.core.stream)
                self.core.stream = NULL
            if self.core.context:
                pa_context_disconnect(self.core.context)
                pa_context_unref(self.core.context)
                self.core.context = NULL
            if self.core.mainloop:
                pa_threaded_mainloop_free(self.core.mainloop)
                self.core.mainloop = NULL

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
        self.core.instance_id = instance_id
        self.core.dB = -200
        self.core.eq.gain = 1.0
        
        if manager == NULL or manager.context == NULL:
            print("error: not initialized manager")
            return

        cdef pa_sample_spec ss
        ss.format = PA_SAMPLE_FLOAT32LE;
        ss.rate = 48000
        ss.channels = 2

        self.core.stream = pa_stream_new(manager.context, "Audiomeeter-Sink", &ss, NULL)
        if self.core.stream == NULL:
            print("error: not created stream")
            return

        cdef int stream_flags = 0x0200 | 0x2000 
        cdef int result = pa_stream_connect_playback(
            self.core.stream, 
            self.core.device_id,
            <pa_buffer_attr*>NULL,
            stream_flags,
            <const void*>NULL,
            <pa_stream*>NULL
        )

        
    def get_device_id(self):
        return self.core.device_id

    def get_dB(self):
        return self.core.dB

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
    
    if core.stream == NULL or pa_stream_get_state(core.stream) != PA_STREAM_READY:
        return

    pa_stream_write(core.stream, data, length, NULL, 0, PA_SEEK_RELATIVE)

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


def init_audio_system():
    global manager

    cdef int i
    cdef pa_mainloop_api * mainloop_api

    if manager == NULL:
        manager = <AudioManager *>calloc(1, sizeof(AudioManager))
        if manager == NULL:
            raise MemoryError("Out of memory!")

        for i in range(MAX_DEVICES):
            manager.devices[i] = NULL

        manager.mainloop = pa_threaded_mainloop_new()
        if manager.mainloop == NULL:
            print("Error: Failed to create mainloop!")
            return

        mainloop_api = pa_threaded_mainloop_get_api(manager.mainloop)

        manager.context = pa_context_new(mainloop_api, b"Audiomeeter-Core")
        if manager.context == NULL:
            print("Error: Failed to create context!")
            return
        

        pa_context_connect(manager.context, NULL, 0, NULL)
        pa_threaded_mainloop_start(manager.mainloop)
        
        while pa_context_get_state(manager.context) != PA_CONTEXT_READY:
            pass

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