# cython: language_level=3

from libc.stdlib cimport free
from libc.string cimport strncpy

# ── C declarations ──────────────────────────────────────────────────────────

cdef extern from "main.h":
    int init_audio_core()

cdef extern from "types.h":
    struct SinkCore:
        char device_id[128]
        int dB

    struct DeviceCore:
        char device_id[128]
        int dB
        int bridged_sinks_count

cdef extern from "devices.h":
    SinkCore *sink_create(const char *device_id)
    int sink_get_dB(SinkCore *sink)
    int sink_set_dB(SinkCore *sink, int dB)
    void sink_link(SinkCore *sink)
    int sink_delete(SinkCore *sink)

    DeviceCore *device_create(const char *device_id)
    int device_get_dB(DeviceCore *device)
    int device_set_dB(DeviceCore *device, int dB)
    void device_link(DeviceCore *device)
    int device_delete(DeviceCore *device)

    int device_set_bridged_sink(DeviceCore *device, SinkCore *sink)
    int device_remove_bridged_sink(DeviceCore *device, SinkCore *sink)

# ── Python API ──────────────────────────────────────────────────────────────

def init():
    """PipeWire motorunu başlat. Tüm işlemlerden önce bir kez çağrılmalı."""
    cdef int res = init_audio_core()
    if res < 0:
        raise RuntimeError("PipeWire audio core başlatılamadı")


cdef class Sink:
    """Çıkış cihazı (hoparlör, kulaklık vb.)"""

    cdef SinkCore *_ptr
    cdef bint _alive

    def __cinit__(self, str device_id):
        cdef bytes b_id = device_id.encode("utf-8")
        self._ptr = sink_create(b_id)
        if self._ptr == NULL:
            raise MemoryError("Sink oluşturulamadı (limit aşıldı)")
        self._alive = True

    def link(self):
        """Portlar PipeWire'a kaydolduktan sonra kabloları bağla."""
        self._check()
        sink_link(self._ptr)

    @property
    def device_id(self) -> str:
        self._check()
        return self._ptr.device_id.decode("utf-8")

    @property
    def dB(self) -> int:
        """Anlık pik ses seviyesi (VU-metre). Salt okunur."""
        self._check()
        return sink_get_dB(self._ptr)

    def delete(self):
        """Sink'i PipeWire grafiğinden kaldır ve belleği serbest bırak."""
        if self._alive:
            sink_delete(self._ptr)
            self._ptr = NULL
            self._alive = False

    cdef inline void _check(self) except *:
        if not self._alive:
            raise RuntimeError("Bu Sink zaten silinmiş")

    def __dealloc__(self):
        self.delete()

    def __repr__(self):
        if self._alive:
            return f"<Sink '{self.device_id}' dB={self.dB}>"
        return "<Sink (deleted)>"


cdef class Device:
    """Giriş cihazı (mikrofon, sanal girdi vb.)"""

    cdef DeviceCore *_ptr
    cdef bint _alive

    def __cinit__(self, str device_id):
        cdef bytes b_id = device_id.encode("utf-8")
        self._ptr = device_create(b_id)
        if self._ptr == NULL:
            raise MemoryError("Device oluşturulamadı (limit aşıldı)")
        self._alive = True

    def link(self):
        """Portlar PipeWire'a kaydolduktan sonra kabloları bağla."""
        self._check()
        device_link(self._ptr)

    @property
    def device_id(self) -> str:
        self._check()
        return self._ptr.device_id.decode("utf-8")

    @property
    def dB(self) -> int:
        """Anlık pik ses seviyesi (VU-metre). Salt okunur."""
        self._check()
        return device_get_dB(self._ptr)

    def bridge(self, Sink sink not None):
        """Bu device'ın sesini verilen sink'e yönlendir."""
        self._check()
        sink._check()
        cdef int res = device_set_bridged_sink(self._ptr, sink._ptr)
        if res == -2:
            raise RuntimeError("Maksimum yönlendirme sınırına ulaşıldı")
        elif res < 0:
            raise RuntimeError("Yönlendirme bağlanamadı")

    def unbridge(self, Sink sink not None):
        """Bu device'dan verilen sink yönlendirmesini kaldır."""
        self._check()
        sink._check()
        cdef int res = device_remove_bridged_sink(self._ptr, sink._ptr)
        if res < 0:
            raise ValueError("Bu sink zaten bağlı değil")

    def delete(self):
        """Device'ı PipeWire grafiğinden kaldır ve belleği serbest bırak."""
        if self._alive:
            device_delete(self._ptr)
            self._ptr = NULL
            self._alive = False

    cdef inline void _check(self) except *:
        if not self._alive:
            raise RuntimeError("Bu Device zaten silinmiş")

    def __dealloc__(self):
        self.delete()

    def __repr__(self):
        if self._alive:
            return f"<Device '{self.device_id}' dB={self.dB}>"
        return "<Device (deleted)>"
