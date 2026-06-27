# -----------------------------------------------------------------------------
# Copyright 2026 abdullah / Ic3zy (https://github.com/Ic3zy)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# This file contains code adapted from the s4-online project:
# https://github.com/Ic3zy/s4-online/blob/main/Scripts/s4online/base/ctx.py
# -----------------------------------------------------------------------------


# TODO: Add support qt signals
class ctx:
    _shared_data = {}
    _callbacks = {}

    def __repr__(self):
        return f"Ctx(data = {len(self._shared_data)}, callbacks = {len(self._callbacks)})"

    def __setattr__(self, name, value):
        if name == "_shared_data" or name == "_callbacks":
            super().__setattr__(name, value)
        else:
            self._shared_data[name] = value
            self.callback_call(name)

    def __getattr__(self, name):
        if name in self._shared_data:
            return self._shared_data[name]
        raise AttributeError(f"'Ctx' nesnesinde '{name}' özelliği bulunamadı.")

    # --- Item Assignment (Ctx['key'] = 'val') ---
    def __setitem__(self, key, value):
        self._shared_data[key] = value
        self.callback_call(key)

    def __getitem__(self, key):
        if key in self._shared_data:
            return self._shared_data[key]
        raise KeyError(f"'{key}' anahtarı Ctx içinde bulunamadı.")

    def __delitem__(self, key):
        if key in self._shared_data:
            del self._shared_data[key]

    def __repr__(self):
        return f"Ctx({self._shared_data})"
    
    def get(self, key, default=None): return self._shared_data.get(key, default)
    def keys(self): return self._shared_data.keys()
    def values(self): return self._shared_data.values()
    def items(self): return self._shared_data.items()


    # --- Callbacks ---
    def callback_call(self, key):
        if self._callbacks.get(key) is not None:
            for callback in self._callbacks[key]:
                callback()

    def add_callback(self, key, callback):
        if self._callbacks.get(key) is None:
            self._callbacks[key] = []

        if self._shared_data.get(key) is not None:
            callback()

        self._callbacks[key].append(callback)
    
    
    def remove_callback(self, key, callback):
        if self._callbacks.get(key) is not None:
            self._callbacks[key].remove(callback)