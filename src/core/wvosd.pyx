# cython: language_level=3
from libcpp cimport bool

cdef extern from "osd.h":
    bool osd_init()
    void osd_destroy()
    void osd_show_volume(int volume, bool muted) nogil
    void osd_dispatch(int timeout_ms) nogil
    void osd_delay_ms(int ms) nogil


cdef class VolumeOSD:
    cdef bint is_initted
    cdef int show_timeout

    def __init__(self):
        self.is_initted = False
        self.show_timeout = 2000
        self.osd_init()

    def osd_init(self):
        if osd_init():
            self.is_initted = True
        else:
            raise RuntimeError("Failed to initialize VolumeOSD")

    cdef void _show_volume(self, int volume, bool muted) noexcept nogil:
        osd_show_volume(volume, muted)

    def show_volume(self, int volume, bool muted):
        if not self.is_initted:
            raise RuntimeError("VolumeOSD is not initialized")

        with nogil:
            self._show_volume(volume, muted)