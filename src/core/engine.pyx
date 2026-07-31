# cython: language_level=3

from libc.stdlib cimport free
from libc.string cimport strncpy

# ── C declarations ──────────────────────────────────────────────────────────

cdef extern from "main.h":
    int init_audio_core()

cdef extern from "types.h":
    struct SinkCore:
        char name[32]
        char device_id[128]
        int dB

    struct DeviceCore:
        char device_id[128]
        int dB
        int bridged_sinks_count

cdef extern from "devices.h":
    SinkCore *sink_create(const char *name, const char *device_id)
    int sink_get_dB(SinkCore *sink)
    int sink_set_dB(SinkCore *sink, int dB)
    int sink_set_gain_from_db(SinkCore *sink, float db)
    void sink_link(SinkCore *sink)
    int sink_delete(SinkCore *sink)

    DeviceCore *device_create(const char *device_id)
    int device_get_dB(DeviceCore *device)
    int device_set_dB(DeviceCore *device, int dB)
    int device_set_gain_from_db(DeviceCore *device, float db)
    void device_link(DeviceCore *device)
    int device_delete(DeviceCore *device)

    int device_set_bridged_sink(DeviceCore *device, SinkCore *sink)
    int device_remove_bridged_sink(DeviceCore *device, SinkCore *sink)

# ── Python API ──────────────────────────────────────────────────────────────

def init():
    cdef int res = init_audio_core()
    if res < 0:
        raise RuntimeError("Failed to initialize PipeWire audio core")


cdef class Sink:
    cdef SinkCore *_ptr
    cdef bint _alive

    def __cinit__(self, str name, str device_id):
        cdef bytes b_name = name.encode("utf-8")
        cdef bytes b_id = device_id.encode("utf-8")
        self._ptr = sink_create(b_name, b_id)
        if self._ptr == NULL:
            raise MemoryError("Failed to create Sink (limit exceeded)")
        self._alive = True

    def link(self):
        # Atomic inside sink_create now, kept for backward compatibility
        pass

    @property
    def name(self) -> str:
        self._check()
        return self._ptr.name.decode("utf-8")

    @property
    def device_id(self) -> str:
        self._check()
        return self._ptr.device_id.decode("utf-8")

    @property
    def dB(self) -> int:
        self._check()
        return sink_get_dB(self._ptr)

    def set_gain_from_db(self, float db):
        self._check()
        return sink_set_gain_from_db(self._ptr, db)

    def delete(self):
        if self._alive:
            sink_delete(self._ptr)
            self._ptr = NULL
            self._alive = False

    cdef inline void _check(self) except *:
        if not self._alive:
            raise RuntimeError("This Sink has already been deleted")

    def __dealloc__(self):
        self.delete()

    def __repr__(self):
        if self._alive:
            return f"<Sink '{self.name}' -> '{self.device_id}' dB={self.dB}>"
        return "<Sink (deleted)>"


cdef class Device:
    cdef DeviceCore *_ptr
    cdef bint _alive

    def __cinit__(self, str device_id):
        cdef bytes b_id = device_id.encode("utf-8")
        self._ptr = device_create(b_id)
        if self._ptr == NULL:
            raise MemoryError("Failed to create Device (limit exceeded)")
        self._alive = True

    def link(self):
        self._check()
        device_link(self._ptr)

    @property
    def device_id(self) -> str:
        self._check()
        return self._ptr.device_id.decode("utf-8")

    @property
    def dB(self) -> int:
        self._check()
        return device_get_dB(self._ptr)
    
    def set_gain_from_db(self, float db):
        self._check()
        return device_set_gain_from_db(self._ptr, db)

    def bridge(self, Sink sink not None):
        self._check()
        sink._check()
        cdef int res = device_set_bridged_sink(self._ptr, sink._ptr)
        if res == -2:
            raise RuntimeError("Maximum bridging limit reached")
        elif res < 0:
            raise RuntimeError("Failed to bridge sink")

    def unbridge(self, Sink sink not None):
        self._check()
        sink._check()
        cdef int res = device_remove_bridged_sink(self._ptr, sink._ptr)
        if res < 0:
            raise ValueError("This sink is not currently bridged")

    def delete(self):
        if self._alive:
            device_delete(self._ptr)
            self._ptr = NULL
            self._alive = False

    cdef inline void _check(self) except *:
        if not self._alive:
            raise RuntimeError("This Device has already been deleted")

    def __dealloc__(self):
        self.delete()

    def __repr__(self):
        if self._alive:
            return f"<Device '{self.device_id}' dB={self.dB}>"
        return "<Device (deleted)>"