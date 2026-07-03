# distutils: libraries = pulse
# audio_core.pyx
# cython: language_level=3

import sys
from libc.stdint cimport uint32_t, uint8_t, int16_t
from libc.stddef cimport size_t
from libc.stdlib cimport malloc, free
from libc.stdio cimport printf
from libc.math cimport log10, sqrt
from libc.string cimport memset

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

    int pa_stream_peek(pa_stream * , const void**, size_t*)
    int pa_stream_drop(pa_stream * )
    int pa_stream_get_state(pa_stream * )

cdef extern from "pulse/sample.h":
    cdef int PA_SAMPLE_S16LE

cdef int PA_CONTEXT_READY = 4
cdef int PA_STREAM_READY = 2

cdef enum: MAX_DEVICES = 32

cdef int callback_interval_steps = 100

cdef struct AudioCore:
    pa_threaded_mainloop * mainloop
    pa_mainloop_api * mainloop_api
    pa_context * context
    pa_stream * stream
    pa_sample_spec ss
    char device_id[256]
    int instance_id
    int is_active
    int current_db

cdef struct AudioManager:
    AudioCore * devices[MAX_DEVICES]
    int step_counter

    # debug
    timespec last_time
    int is_init

cdef AudioManager * manager = NULL

cdef void context_state_callback(pa_context * context, void * userdata) noexcept nogil:
    pass


cdef inline double calculate_rms(int16_t * samples, size_t num_samples) noexcept nogil:
    cdef size_t i
    cdef double sum_squares = 0.0

    for i in range(num_samples):
        sum_squares += ( < double > samples[i] * <double > samples[i])

    return sqrt(sum_squares / num_samples) if num_samples > 0 else 0.0

cdef inline int rms_to_db(double rms) noexcept nogil:
    cdef double db = -200.0

    if rms > 0.1:
        db = 20.0 * log10(rms / 32768.0)

    if db > 12.0:
        return 12
    if db < -200.0:
        return -200
    return < int > db


cdef inline void route_audio(int src_id, const void * data, size_t length) noexcept nogil:
    if src_id == 1 and manager != NULL and manager.devices[
            2] != NULL and manager.devices[2].is_active:
        pass

# main audio callback
# stream, 443 call / sec
cdef void stream_read_callback(pa_stream * stream, size_t length, void * userdata) noexcept nogil:
    cdef AudioCore * current_core = <AudioCore * >userdata
    cdef const void * data = NULL
    cdef size_t data_length = 0
    cdef double rms = 0.0

    cdef timespec now

    cdef double elapsed = 0.0

    if manager == NULL:
        return

    if current_core == NULL or current_core.is_active == 0:
        return

    if pa_stream_peek(stream, & data, & data_length) < 0:
        return

    if data_length > 0 and data != NULL:
        if manager.step_counter >= callback_interval_steps:

            if manager.is_init != 0:
                clock_gettime(CLOCK_MONOTONIC, & now)

                elapsed = (now.tv_sec - manager.last_time.tv_sec) + \
                    (now.tv_nsec - manager.last_time.tv_nsec) / 1000000000.0
                printf(
                    "[%d] Elapsed: %f len: %d \n",
                    current_core.instance_id,
                    elapsed,
                    data_length)

                manager.last_time = now
            else:
                clock_gettime(CLOCK_MONOTONIC, & manager.last_time)
                manager.is_init = 1

            rms = calculate_rms(< int16_t*>data, data_length  // sizeof(int16_t))

            current_core.current_db = rms_to_db(rms)

            manager.step_counter = 0

            printf(
                "[%d] RMS: %f, DB: %d\n",
                current_core.instance_id,
                rms,
                current_core.current_db)

        else:
            manager.step_counter += 1

        route_audio(current_core.instance_id, data, data_length)

    pa_stream_drop(stream)


cdef class AudioRecorder:
    cdef AudioCore * core

    def __cinit__(self, bytes device_id, int instance_id):
        global manager
        if manager == NULL:
            raise RuntimeError(
                "The system must be initialized in RAM by calling 'init_audio_system()' first!"
            )

        if instance_id < 0 or instance_id >= MAX_DEVICES:
            raise ValueError(
                f"Instance ID must be between 0 and {MAX_DEVICES - 1}!"
            )

        self.core = <AudioCore *>malloc(sizeof(AudioCore))
        if self.core == NULL:
            raise MemoryError("Failed to allocate RAM for the device at C-level.")

        self.core.mainloop = NULL
        self.core.context = NULL
        self.core.stream = NULL
        self.core.ss.format = PA_SAMPLE_S16LE
        self.core.ss.rate = 48000
        self.core.ss.channels = 2
        self.core.instance_id = instance_id
        self.core.is_active = 1

        snprintf(
            self.core.device_id,
            sizeof(
                self.core.device_id),
            "%s",
            device_id)

        manager.devices[instance_id] = self.core

    def start(self):
        cdef int stream_flags = 2

        cdef pa_buffer_attr * attr = NULL

        with nogil:
            self.core.mainloop = pa_threaded_mainloop_new()
            self.core.mainloop_api = pa_threaded_mainloop_get_api(self.core.mainloop)

            self.core.context = pa_context_new(
                self.core.mainloop_api, b"CythonAudioRecorder")
            pa_context_set_state_callback(
                self.core.context, context_state_callback, NULL)
            pa_context_connect(self.core.context, NULL, 0, NULL)

            pa_threaded_mainloop_start(self.core.mainloop)

            while pa_context_get_state(self.core.context) != PA_CONTEXT_READY:
                pass

            self.core.stream = pa_stream_new(self.core.context, b"RecordStream", & self.core.ss, NULL)
            pa_stream_set_read_callback(self.core.stream, stream_read_callback, < void * >self.core)

            attr = <pa_buffer_attr * >malloc(sizeof(pa_buffer_attr))
            if attr != NULL:
                memset(attr, 0, sizeof(pa_buffer_attr))

                attr.maxlength = <uint32_t > -1
                attr.tlength = <uint32_t > -1
                attr.prebuf = <uint32_t > -1
                attr.minreq = <uint32_t > -1

                attr.fragsize = 128 * 2 * 2

            pa_stream_connect_record(
                self.core.stream,
                self.core.device_id,
                attr,
                stream_flags)

            while pa_stream_get_state(self.core.stream) != PA_STREAM_READY:
                pass

            if attr != NULL:
                free(attr)

    @property
    def dB(self):
        return self.core.current_db

    def stop(self):
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


def init_audio_system():
    global manager
    cdef int i

    if manager == NULL:
        manager = < AudioManager * >malloc(sizeof(AudioManager))
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