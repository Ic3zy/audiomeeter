cdef extern from "rt_biquad/include/rt_biquad.h" nogil:

    cdef struct rt_biquad_state:
        pass

    cdef struct rt_band:
        pass

    rt_band* create_band(
        float start_hz,
        float end_hz,
        float db_gain,
        float sample_rate
    )

    void update_band(
        rt_band *band,
        float start_hz,
        float end_hz,
        float db_gain,
        float sample_rate
    )

    void destroy_band(rt_band *band)

    void filter_from_hz_list(
        rt_band *bands,
        float *samples,
        int length,
        float sample_rate,
        int band_count
    )