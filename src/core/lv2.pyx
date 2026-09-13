# cython: language_level=3

from libc.stdlib cimport malloc, free
from libc.stdint cimport uint32_t
from libcpp cimport bool as cbool

cdef extern from "lv2_manager.h":
    struct Output:
        float *left
        float *right

    ctypedef struct Lv2ParamInfo:
        uint32_t port_index
        char *symbol
        char *name
        float min_val
        float max_val
        float default_val
        float current_val
        cbool is_toggle

    ctypedef struct Lv2FilterInfo:
        size_t index
        char *name
        char *uri
        cbool enabled
        Lv2ParamInfo *params
        size_t param_count

    ctypedef struct Lv2PluginAvailableInfo:
        char *name
        char *uri
        char *category

    ctypedef struct Lv2PluginAvailableList:
        Lv2PluginAvailableInfo *plugins
        size_t count

    ctypedef struct Lv2Manager:
        pass

    Lv2Manager *lv2_manager_create(int n_samples, int min_filter_count, int sample_rate) nogil
    void lv2_manager_destroy(Lv2Manager *manager) nogil
    Lv2PluginAvailableList lv2_manager_get_available_plugins(Lv2Manager *manager) nogil
    void lv2_manager_free_available_plugins(Lv2PluginAvailableList *list) nogil
    int lv2_manager_add_filter(Lv2Manager *manager, const char *target_uri) nogil
    cbool lv2_manager_remove_filter(Lv2Manager *manager, size_t index) nogil
    cbool lv2_manager_move_filter(Lv2Manager *manager, size_t old_index, size_t new_index) nogil
    cbool lv2_manager_swap_filters(Lv2Manager *manager, size_t index_a, size_t index_b) nogil
    cbool lv2_manager_set_bypass(Lv2Manager *manager, size_t index, cbool enabled) nogil
    cbool lv2_manager_get_filter_info(Lv2Manager *manager, size_t index, Lv2FilterInfo *out_info) nogil
    void lv2_manager_free_filter_info(Lv2FilterInfo *info) nogil
    cbool lv2_manager_set_param(Lv2Manager *manager, size_t filter_index, const char *symbol, float value) nogil
    float lv2_manager_get_param(Lv2Manager *manager, size_t filter_index, const char *symbol) nogil
    Output *lv2_manager_process(Lv2Manager *manager, const float *in_l, const float *in_r, int n_samples) nogil


cdef class Lv2Chain:
    """
    Python wrapper class for the Lv2Manager C library.
    Provides high-level methods returning Python list[dict] structures for 
    building Plugin Add Menus and Plugin Control GUIs with GIL release for heavy operations.
    """
    cdef Lv2Manager *_ptr
    cdef bint _alive

    def __cinit__(self, int n_samples=1024, int min_filter_count=4, int sample_rate=48000):
        cdef Lv2Manager *ptr = NULL
        with nogil:
            ptr = lv2_manager_create(n_samples, min_filter_count, sample_rate)
        if ptr == NULL:
            raise MemoryError("Failed to initialize Lv2Manager C instance")
        self._ptr = ptr
        self._alive = True

    cdef inline void _check(self) except *:
        if not self._alive or self._ptr == NULL:
            raise RuntimeError("This Lv2Chain instance has already been destroyed")

    def destroy(self):
        """Explicitly frees C memory allocated for Lv2Manager without holding GIL."""
        cdef Lv2Manager *ptr = self._ptr
        if self._alive and ptr != NULL:
            self._ptr = NULL
            self._alive = False
            with nogil:
                lv2_manager_destroy(ptr)

    def __dealloc__(self):
        self.destroy()

    def get_available_plugins(self) -> list:
        """
        Discovers all installed LV2 plugins on the system without holding Python GIL during discovery.
        
        Returns:
            list[dict]: List of plugin dictionaries, e.g.:
            [
                {
                    "name": "LSP Multi-Sampler x12 Stereo",
                    "uri": "http://lsp-plug.in/plugins/lv2/multisampler_x12",
                    "category": "Sampler"
                },
                ...
            ]
        """
        self._check()
        cdef Lv2Manager *ptr = self._ptr
        cdef Lv2PluginAvailableList list_info
        
        with nogil:
            list_info = lv2_manager_get_available_plugins(ptr)

        cdef list result = []
        cdef size_t i
        cdef str name_str, uri_str, cat_str

        try:
            for i in range(list_info.count):
                name_str = list_info.plugins[i].name.decode("utf-8") if list_info.plugins[i].name != NULL else ""
                uri_str  = list_info.plugins[i].uri.decode("utf-8") if list_info.plugins[i].uri != NULL else ""
                cat_str  = list_info.plugins[i].category.decode("utf-8") if list_info.plugins[i].category != NULL else "Plugin"

                result.append({
                    "name": name_str,
                    "uri": uri_str,
                    "category": cat_str,
                })
        finally:
            with nogil:
                lv2_manager_free_available_plugins(&list_info)

        return result

    def add_filter(self, str target_uri) -> int:
        """
        Appends a filter to the chain by URI or search query substring without holding GIL during instantiation.
        
        Returns:
            int: The 0-based index assigned to the new filter in the chain.
        """
        self._check()
        cdef Lv2Manager *ptr = self._ptr
        cdef bytes b_uri = target_uri.encode("utf-8")
        cdef const char *c_uri = b_uri
        cdef int idx

        with nogil:
            idx = lv2_manager_add_filter(ptr, c_uri)

        if idx < 0:
            raise ValueError(f"Plugin matching '{target_uri}' could not be found or instantiated")
        return idx

    def remove_filter(self, size_t index) -> bool:
        """Removes a filter at the given index from the chain."""
        self._check()
        cdef Lv2Manager *ptr = self._ptr
        cdef cbool res
        with nogil:
            res = lv2_manager_remove_filter(ptr, index)
        return bool(res)

    def move_filter(self, size_t old_index, size_t new_index) -> bool:
        """Moves a filter from old_index to new_index in the chain."""
        self._check()
        cdef Lv2Manager *ptr = self._ptr
        cdef cbool res
        with nogil:
            res = lv2_manager_move_filter(ptr, old_index, new_index)
        return bool(res)

    def swap_filters(self, size_t index_a, size_t index_b) -> bool:
        """Swaps the chain positions of filter_a and filter_b."""
        self._check()
        cdef Lv2Manager *ptr = self._ptr
        cdef cbool res
        with nogil:
            res = lv2_manager_swap_filters(ptr, index_a, index_b)
        return bool(res)

    def set_bypass(self, size_t index, bint enabled) -> bool:
        """Sets the active/bypass state of a filter in the chain."""
        self._check()
        cdef Lv2Manager *ptr = self._ptr
        cdef cbool c_enabled = <cbool>enabled
        cdef cbool res
        with nogil:
            res = lv2_manager_set_bypass(ptr, index, c_enabled)
        return bool(res)

    def get_filter_info(self, size_t index) -> dict:
        """
        Queries complete metadata and configurable parameter details for a single filter.
        
        Returns:
            dict: Detailed dictionary structured for rendering a Plugin Control GUI.
        """
        self._check()
        cdef Lv2Manager *ptr = self._ptr
        cdef Lv2FilterInfo info
        cdef cbool ok

        with nogil:
            ok = lv2_manager_get_filter_info(ptr, index, &info)

        if not ok:
            raise IndexError(f"Filter index {index} out of range")

        cdef list params = []
        cdef size_t i
        cdef dict p_dict, res

        try:
            for i in range(info.param_count):
                p_dict = {
                    "port_index": info.params[i].port_index,
                    "symbol": info.params[i].symbol.decode("utf-8") if info.params[i].symbol != NULL else "",
                    "name": info.params[i].name.decode("utf-8") if info.params[i].name != NULL else "",
                    "min_val": info.params[i].min_val,
                    "max_val": info.params[i].max_val,
                    "default_val": info.params[i].default_val,
                    "current_val": info.params[i].current_val,
                    "is_toggle": True if info.params[i].is_toggle else False,
                }
                params.append(p_dict)

            res = {
                "index": info.index,
                "name": info.name.decode("utf-8") if info.name != NULL else "",
                "uri": info.uri.decode("utf-8") if info.uri != NULL else "",
                "enabled": True if info.enabled else False,
                "param_count": info.param_count,
                "params": params,
            }
        finally:
            with nogil:
                lv2_manager_free_filter_info(&info)

        return res

    def get_all_filters(self) -> list:
        """
        Returns metadata and parameters for all active filters currently in the chain.
        """
        self._check()
        cdef list result = []
        cdef size_t idx = 0
        while True:
            try:
                info_dict = self.get_filter_info(idx)
                result.append(info_dict)
                idx += 1
            except IndexError:
                break
        return result

    def set_param(self, size_t filter_index, str symbol, float value) -> bool:
        """Updates a filter control parameter value by symbol string."""
        self._check()
        cdef Lv2Manager *ptr = self._ptr
        cdef bytes b_sym = symbol.encode("utf-8")
        cdef const char *c_sym = b_sym
        cdef cbool res

        with nogil:
            res = lv2_manager_set_param(ptr, filter_index, c_sym, value)
        return bool(res)

    def get_param(self, size_t filter_index, str symbol) -> float:
        """Reads a filter control parameter value by symbol string."""
        self._check()
        cdef Lv2Manager *ptr = self._ptr
        cdef bytes b_sym = symbol.encode("utf-8")
        cdef const char *c_sym = b_sym
        cdef float res

        with nogil:
            res = lv2_manager_get_param(ptr, filter_index, c_sym)
        return res

    def process(self, in_left, in_right) -> tuple:
        """
        Processes audio through the LV2 chain releasing the GIL during DSP computations.
        
        Args:
            in_left (sequence of float): Left channel input audio samples.
            in_right (sequence of float): Right channel input audio samples.
            
        Returns:
            tuple[list[float], list[float]]: (out_left, out_right) lists of processed float samples.
        """
        self._check()

        cdef size_t len_l = len(in_left) if in_left is not None else 0
        cdef size_t len_r = len(in_right) if in_right is not None else 0
        cdef int n_samples = <int>(len_l if len_l > len_r else len_r)

        if n_samples <= 0:
            return ([], [])

        cdef float *c_in_l = NULL
        cdef float *c_in_r = NULL
        cdef int i

        if len_l > 0:
            c_in_l = <float *>malloc(sizeof(float) * n_samples)
            if c_in_l == NULL:
                raise MemoryError("Failed to allocate memory for left channel input buffer")
            for i in range(n_samples):
                c_in_l[i] = <float>(in_left[i] if i < len_l else 0.0)

        if len_r > 0:
            c_in_r = <float *>malloc(sizeof(float) * n_samples)
            if c_in_r == NULL:
                if c_in_l != NULL:
                    free(c_in_l)
                raise MemoryError("Failed to allocate memory for right channel input buffer")
            for i in range(n_samples):
                c_in_r[i] = <float>(in_right[i] if i < len_r else 0.0)

        cdef Lv2Manager *ptr = self._ptr
        cdef Output *out_ptr = NULL
        cdef list out_l = []
        cdef list out_r = []

        try:
            # RELEASE GIL DURING DSP AUDIO PROCESSING
            with nogil:
                out_ptr = lv2_manager_process(ptr, c_in_l, c_in_r, n_samples)

            if out_ptr == NULL or out_ptr.left == NULL or out_ptr.right == NULL:
                raise RuntimeError("lv2_manager_process failed to return valid output buffers")

            out_l = [out_ptr.left[i] for i in range(n_samples)]
            out_r = [out_ptr.right[i] for i in range(n_samples)]
            return (out_l, out_r)
        finally:
            if c_in_l != NULL:
                free(c_in_l)
            if c_in_r != NULL:
                free(c_in_r)

    def test_process(self, in_left, in_right) -> tuple:
        """Alias for process(in_left, in_right) used for testing audio processing."""
        return self.process(in_left, in_right)
