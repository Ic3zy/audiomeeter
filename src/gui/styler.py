from PySide6.QtCore import QObject, QFileSystemWatcher
from pathlib import Path

_styler_instance = None

# For developers
class Hot_Reloader(QObject):
    def __init__(self, src_path="src/assets/styles"):
        super().__init__()
        self.styles_path = src_path
        self._style_to_qt_object = {}
        self._path_to_name = {}

        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self.on_file_changed)

        self.start_watcher()

    def add_style(self, name, qt_object, current_style_content=None):
        if name not in self._style_to_qt_object:
            self._style_to_qt_object[name] = []
        
        self._style_to_qt_object[name].append(qt_object)
        
        if current_style_content:
            qt_object.setStyleSheet(current_style_content)

    def get_style_name(self, path):
        return self._path_to_name.get(path)

    def start_watcher(self):
        styles_dir = Path(self.styles_path)
        
        if not styles_dir.exists():
            raise FileNotFoundError(f"Styles directory not found: {styles_dir}")

        for file_path in styles_dir.iterdir():
            if file_path.is_file() and file_path.suffix in ['.qss', '.css']:
                path_str = str(file_path)
                print(f"path_str: {path_str}")
                self._path_to_name[path_str] = file_path.stem
                self.watcher.addPath(path_str)

    def read_qss_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"error reading file: {path}")

    def on_file_changed(self, path):
        print(f"on_file_changed: {path}")
        self.watcher.addPath(path)
        
        name = self.get_style_name(path)
        if not name or name not in self._style_to_qt_object:
            return
        
        content = self.read_qss_file(path)
        if content is None:
            return
            
        print(f"{name} stili güncellendi!")
        for qt_object in self._style_to_qt_object[name]:
            qt_object.setStyleSheet(content)


class Styler:
    def __init__(self, styles_path="src/assets/styles"):
        global _styler_instance
        self.styles_path = styles_path
        self.style_sheets = {}
        self.load_styles()
        self.hot_reloader = Hot_Reloader(styles_path)
        _styler_instance = self

    @classmethod
    def instance(cls):
        return _styler_instance

    def __repr__(self):
        return f"Styler(styles_path={self.styles_path}, top_styles={len(self.style_sheets)})"

    def load_styles(self):
        styles_dir = Path(self.styles_path)
        if not styles_dir.exists():
            return
            
        for file_path in styles_dir.iterdir():
            if file_path.is_file(): 
                with open(file_path, "r", encoding="utf-8") as f:
                    self.style_sheets[file_path.stem] = f.read()

    def set_style(self, name, qt_object):
        current_style = self.style_sheets.get(name, "")
        if current_style is None:
            raise ValueError(f"Style not found: {name}")
        
        self.hot_reloader.add_style(name, qt_object, current_style)

    def __getitem__(self, key):
        return self.style_sheets[key]

    def __setitem__(self, key, value):
        self.style_sheets[key] = value

    def __delitem__(self, key):
        del self.style_sheets[key]

