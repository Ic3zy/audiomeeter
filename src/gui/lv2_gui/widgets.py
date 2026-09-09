import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSlider,
    QVBoxLayout,
    QWidget,
    QCheckBox,
    QGraphicsDropShadowEffect,
)

from PySide6.QtWidgets import QScrollArea, QSizePolicy

colors = {
    "plugin_wd_bg": "#033d43",
    "plugin_wd_bg_bottom": "#021f24",
    "plugin_border": "#0e5a63",
    "plugin_border_hover": "#2dd4c8",
    "plugin_label": "#d6f5f5",
}


class Lv2ParamSlider(QSlider):
    def __init__(self, param_widget, min_val, max_val, default_val):
        super().__init__(Qt.Orientation.Horizontal)
        self.param_widget = param_widget
        if isinstance(default_val, float):
            default_val = int(default_val)

        self.default_val = default_val

        self.setFixedHeight(30)
        self.setFixedWidth(200)

        self.setMinimum(int(min_val))
        self.setMaximum(int(max_val))
        self.setValue(int(default_val))

    def setValue(self, value):
        super().setValue(value)
        if hasattr(self, "param_widget") and self.param_widget:
            self.param_widget.set_value(value)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setValue(self.default_val)
        else:
            super().mouseDoubleClickEvent(event)


class Lv2ParamWidget:
    def __init__(self, param_info):
        self.param_info = param_info
        self.param_name = param_info["name"]
        self.param_symbol = param_info["symbol"]
        self.param_min = param_info["min_val"]
        self.param_max = param_info["max_val"]
        self.param_default = param_info["default_val"]
        self.param_current = param_info["current_val"]
        self.is_toggle = param_info["is_toggle"]

        self.widget = None
        self.init_widget()

        self.value_changed_callbacks = []

    def add_value_changed_callback(self, callback):
        if callback in self.value_changed_callbacks:
            raise ValueError(f"Callback already added: {callback}")

        self.value_changed_callbacks.append(callback)

    def init_widget(self):
        if self.is_toggle:
            self.init_toggle()
        else:
            self.init_slider()

    def init_toggle(self):
        self.name_label = QLabel(self.param_name)
        self.value_label = QLabel(f"{self.param_current}")
        self.toggle = QCheckBox()

        self.toggle.setChecked(int(self.param_current))
        self.toggle.stateChanged.connect(lambda state: self.set_value(state))

        layout = QVBoxLayout()

        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.name_label)

        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addWidget(self.toggle)

        self.widget = QWidget()
        self.widget.setLayout(layout)

    def init_slider(self):
        mins = self.param_min
        maxs = self.param_max
        default = self.param_default

        self.name_label = QLabel(self.param_name)
        self.value_label = QLabel(f"{self.param_current:0.0f}")
        self.slider = Lv2ParamSlider(self, mins, maxs, default)

        self.slider.valueChanged.connect(lambda v: self.set_value(f"{v}"))

        h_layout = QHBoxLayout()

        layout = QVBoxLayout()

        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.name_label)

        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        h_layout.addWidget(self.slider)
        h_layout.addWidget(self.value_label)

        h_layout.setSpacing(8)
        h_layout.setContentsMargins(0, 0, 0, 0)

        h_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        layout.addLayout(h_layout)

        self.widget = QWidget()
        self.widget.setLayout(layout)

    def set_value(self, value):
        self.param_current = value
        print(f"[{self.param_name}] Yeni Değer: {value}")
        self.value_label.setText(f"{value}")

        for callback in self.value_changed_callbacks:
            callback(value)


class Lv2PluginWidget(QWidget):

    def __init__(self, param_info):
        super().__init__()
        self.param_info = param_info
        self.param_name = param_info["name"]
        self.init_widget()

    def init_widget(self):
        self.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(14, 12, 14, 12)

        label = QLabel(self.param_name)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                color: #eafdff;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.5px;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)

        self.setStyleSheet(f"""
    Lv2PluginWidget {{
        background: qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 {colors["plugin_wd_bg"]},
            stop:1 {colors["plugin_wd_bg_bottom"]}
        );
        border: 1px solid {colors["plugin_border"]};
        border-radius: 10px;
    }}
    Lv2PluginWidget:hover {{
        border: 1px solid {colors["plugin_border_hover"]};
    }}
""")


class PluginListContainer(QWidget):
    def __init__(self, plugin_infos):
        super().__init__()

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setAlignment(Qt.AlignTop)

        for param_info in plugin_infos:
            plugin_widget = Lv2PluginWidget(param_info)
            plugin_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            content_layout.addWidget(plugin_widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)


class MainWindow(QMainWindow):
    def __init__(self, param_data):
        super().__init__()
        self.setWindowTitle("LV2 Select Plugin")
        self.setFixedSize(900, 545)

        self.param_objs = []

        # for p in param_data:
        #     self.param_objs.append(Lv2PluginWidget(p))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(PluginListContainer(param_data))

        # for param_obj in self.param_objs:
        #     layout.addWidget(param_obj)

    def __init__EX(self, param_data):
        super().__init__()
        self.setWindowTitle("LV2 Parametre Testi")
        self.resize(250, 350)

        self.param_objs = []
        if isinstance(param_data, dict):
            self.param_objs.append(Lv2ParamWidget(param_data))

        elif isinstance(param_data, list):
            for param in param_data:
                self.param_objs.append(Lv2ParamWidget(param))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        for param_obj in self.param_objs:
            layout.addWidget(param_obj)


if __name__ == "__main__":
    # sample_dict = {
    #     "port_index": 0,
    #     "symbol": "reduction",
    #     "name": "Reduction amount",
    #     "min_val": 0.0,
    #     "max_val": 20.0,
    #     "default_val": 10.0,
    #     "current_val": 20.0,
    #     "is_toggle": False,
    # }

    samples = [
        {
            "name": "Audio File",
            "uri": "http://kxstudio.sf.net/carla/plugins/audiofile",
            "category": "Utility Plugin",
        },
        {
            "name": "Audio Gain(Mono)",
            "uri": "http://kxstudio.sf.net/carla/plugins/audiogain",
            "category": "Utility Plugin",
        },
        {
            "name": "Audio Gain (Stereo)",
            "uri": "http://kxstudio.sf.net/carla/plugins/audiogain_s",
            "category": "Utility Plugin",
        },
        {
            "name": "Big Meter",
            "uri": "http://kxstudio.sf.net/carla/plugins/bigmeter",
            "category": "Utility Plugin",
        },
        {
            "name": "Carla-Patchbay",
            "uri": "http://kxstudio.sf.net/carla/plugins/carlapatchbay",
            "category": "Plugin",
        },
        {
            "name": "Carla-Patchbay (16chan)",
            "uri": "http://kxstudio.sf.net/carla/plugins/carlapatchbay16",
            "category": "Plugin",
        },
        {
            "name": "Carla-Patchbay (32chan)",
            "uri": "http://kxstudio.sf.net/carla/plugins/carlapatchbay32",
            "category": "Plugin",
        },
        {
            "name": "Carla-Patchbay (sidechain)",
            "uri": "http://kxstudio.sf.net/carla/plugins/carlapatchbay3s",
            "category": "Plugin",
        },
        {
            "name": "Carla-Patchbay (64chan)",
            "uri": "http://kxstudio.sf.net/carla/plugins/carlapatchbay64",
            "category": "Plugin",
        },
        {
            "name": "Carla-Patchbay (CV)",
            "uri": "http://kxstudio.sf.net/carla/plugins/carlapatchbaycv",
            "category": "Plugin",
        },
        {
            "name": "Carla-Rack",
            "uri": "http://kxstudio.sf.net/carla/plugins/carlarack",
            "category": "Plugin",
        },
        {
            "name": "LFO",
            "uri": "http://kxstudio.sf.net/carla/plugins/lfo",
            "category": "Utility Plugin",
        },
        {
            "name": "MIDI Channel A/B",
            "uri": "http://kxstudio.sf.net/carla/plugins/midichanab",
            "category": "Utility Plugin",
        },
        {
            "name": "MIDI Channel Filter",
            "uri": "http://kxstudio.sf.net/carla/plugins/midichanfilter",
            "category": "Utility Plugin",
        },
        {
            "name": "MIDI Channelize",
            "uri": "http://kxstudio.sf.net/carla/plugins/midichannelize",
            "category": "Utility Plugin",
        },
        {
            "name": "MIDI File",
            "uri": "http://kxstudio.sf.net/carla/plugins/midifile",
            "category": "Utility Plugin",
        },
        {
            "name": "MIDI Gain",
            "uri": "http://kxstudio.sf.net/carla/plugins/midigain",
            "category": "Utility Plugin",
        },
        {
            "name": "MIDI Join",
            "uri": "http://kxstudio.sf.net/carla/plugins/midijoin",
            "category": "Utility Plugin",
        },
        {
            "name": "MIDI Pattern",
            "uri": "http://kxstudio.sf.net/carla/plugins/midipattern",
            "category": "Utility Plugin",
        },
        {
            "name": "MIDI Split",
            "uri": "http://kxstudio.sf.net/carla/plugins/midisplit",
            "category": "Utility Plugin",
        },
        {
            "name": "MIDI Transpose",
            "uri": "http://kxstudio.sf.net/carla/plugins/miditranspose",
            "category": "Utility Plugin",
        },
        {
            "name": "LSP A/B Tester x2 Mono",
            "uri": "http://lsp-plug.in/plugins/lv2/ab_tester_x2_mono",
            "category": "Utility Plugin",
        },
        {
            "name": "LSP A/B Tester x2 Stereo",
            "uri": "http://lsp-plug.in/plugins/lv2/ab_tester_x2_stereo",
            "category": "Utility Plugin",
        },
        {
            "name": "LSP A/B Tester x4 Mono",
            "uri": "http://lsp-plug.in/plugins/lv2/ab_tester_x4_mono",
            "category": "Utility Plugin",
        },
        {
            "name": "LSP A/B Tester x4 Stereo",
            "uri": "http://lsp-plug.in/plugins/lv2/ab_tester_x4_stereo",
            "category": "Utility Plugin",
        },
        {
            "name": "LSP A/B Tester x8 Mono",
            "uri": "http://lsp-plug.in/plugins/lv2/ab_tester_x8_mono",
            "category": "Utility Plugin",
        },
        {
            "name": "LSP A/B Tester x8 Stereo",
            "uri": "http://lsp-plug.in/plugins/lv2/ab_tester_x8_stereo",
            "category": "Utility Plugin",
        },
        {
            "name": "LSP Artistic Delay Mono",
            "uri": "http://lsp-plug.in/plugins/lv2/art_delay_mono",
            "category": "Delay Plugin",
        },
        {
            "name": "LSP Artistic Delay Stereo",
            "uri": "http://lsp-plug.in/plugins/lv2/art_delay_stereo",
            "category": "Delay Plugin",
        },
        {
            "name": "LSP Autogain Mono",
            "uri": "http://lsp-plug.in/plugins/lv2/autogain_mono",
            "category": "Envelope Plugin",
        },
    ]

    app = QApplication(sys.argv)
    window = MainWindow(samples)
    window.show()
    sys.exit(app.exec())
