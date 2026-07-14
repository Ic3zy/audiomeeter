DEF MAX_DEVICES = 32
DEF MAX_ROUTES_PER_DEVICE = 8
DEF MAX_NAME_LEN = 32
DEF BUFFER_LEN = 2048
DEF SAMPLES_COUNT = BUFFER_LEN // 4
DEF PW_VERSION_STREAM_EVENTS = 2 

cdef struct AudioCore
cdef struct Sink_Core

cdef struct Equalizer:
    rt_band *bass_band
    rt_band *mid_band
    rt_band *treble_band

    double gain

cdef struct Buffer:
    float samples[SAMPLES_COUNT]

cdef struct SinkCore:
    AudioCore * core
    Equalizer eq
    char device_id[128]
    int instance_id
    int dB_counter
    int dB

    int top_updateable
    int active_buffer_ids[MAX_ROUTES_PER_DEVICE]
    Buffer buffers[MAX_DEVICES]

cdef struct AudioCore:
    pw_stream *stream
    Equalizer eq

    Sink_Core * bridged_sinks[MAX_ROUTES_PER_DEVICE]
    int active_bridge_count

    char device_id[256]
    int instance_id
    int is_active
    int dB
    
cdef struct AudioManager:
    pw_thread_loop * mainloop
    AudioCore * listen_devices[MAX_DEVICES]
    Sink_Core * sink_devices[MAX_DEVICES]

    timespec last_tick
