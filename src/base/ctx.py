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

import json, os

from pathlib import Path

def get_config_path() -> Path:
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    
    if xdg_config:
        config_dir = Path(xdg_config) / "audiomeeter"
    else:
        config_dir = Path.home() / ".config" / "audiomeeter"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    
    return config_dir / "config.json"

class ctx:
    _shared_data = {}
    _callbacks = {}



    def __repr__(self):
        return f"Ctx(data = {len(self._shared_data)}, callbacks = {len(self._callbacks)})"

    def __setattr__(self, name, value):
        # print(f"setattr: {name}")
        if name == "_shared_data" or name == "_callbacks":
            super().__setattr__(name, value)
        else:
            if self._shared_data.get(name) == value:
                return
            
            self._shared_data[name] = value
            self.callback_call(name)

    def __getattr__(self, name):
        if name in self._shared_data:
            return self._shared_data[name]
        raise AttributeError(f"'Ctx' nesnesinde '{name}' özelliği bulunamadı.")

    # --- Item Assignment (Ctx['key'] = 'val') ---
    def __setitem__(self, key, value):
        # print(f"setitem: {key}")
        if self._shared_data.get(key) == value:
            return
        
        self._shared_data[key] = value
        self.callback_call(key)

    def __contains__(self, key):
        return key in self._shared_data

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

    #
    def load_config(self):
        saved_ctx_path = get_config_path()
        if saved_ctx_path.exists():
            self.load_from_file(saved_ctx_path)
            print(f"config: {self.to_json_string()}")

    def on_quit(self):
        self.save_to_file(get_config_path())

    def save_to_file(self, path: Path):
        with open(path, "w") as f:
            print(f"save_to_file: {path}, {self.to_json_string()}")
            f.write(self.to_json_string())

    def reset_config(self):
        with open(get_config_path(), "w") as f:
            f.write("{}")

    def to_json_string(self) -> str:
        serializable_dump = {}
        for k, v in self._shared_data.items():
            try:
                json.dumps(v)
                serializable_dump[k] = v
            except (TypeError, OverflowError):
                continue
        return json.dumps(serializable_dump, indent=4)

    def load_from_dict(self, data_dict: dict, trigger_callbacks: bool = True):
        for k, v in data_dict.items():
            self._shared_data[k] = v

        if trigger_callbacks:
            for k in data_dict.keys():
                self.callback_call(k)

    def load_from_file(self, path: Path):
        if not path.exists():
            return {}
        try:
            with open(path, "r") as f:
                data_dict = json.load(f)
                self.load_from_dict(data_dict, trigger_callbacks=True)
        except Exception as e:
            print(f"Config loading error: {e}")
            import traceback
            traceback.print_exc()
            
            return {}
