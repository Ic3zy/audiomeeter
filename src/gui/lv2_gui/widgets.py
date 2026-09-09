import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSlider,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)


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


class MainWindow(QMainWindow):
    def __init__(self, param_data):
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
            layout.addWidget(param_obj.widget)


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
            "port_index": 0,
            "symbol": "reduction",
            "name": "Reduction amount",
            "min_val": 0.0,
            "max_val": 20.0,
            "default_val": 10.0,
            "current_val": 20.0,
            "is_toggle": False,
        },
        {
            "port_index": 1,
            "symbol": "noise_scaling_type",
            "name": "Type of reduction",
            "min_val": 0.0,
            "max_val": 2.0,
            "default_val": 2.0,
            "current_val": 2.0,
            "is_toggle": False,
        },
        {
            "port_index": 2,
            "symbol": "offset",
            "name": "Reduction strength",
            "min_val": 0.0,
            "max_val": 24.0,
            "default_val": 2.0,
            "current_val": 2.0,
            "is_toggle": False,
        },
        {
            "port_index": 3,
            "symbol": "postfilter",
            "name": "Post-filter threshold",
            "min_val": -10.0,
            "max_val": 10.0,
            "default_val": -10.0,
            "current_val": -10.0,
            "is_toggle": False,
        },
        {
            "port_index": 4,
            "symbol": "smoothing",
            "name": "Smoothing",
            "min_val": 0.0,
            "max_val": 100.0,
            "default_val": 0.0,
            "current_val": 0.0,
            "is_toggle": False,
        },
        {
            "port_index": 5,
            "symbol": "whitening",
            "name": "Residual whitening",
            "min_val": 0.0,
            "max_val": 100.0,
            "default_val": 0.0,
            "current_val": 0.0,
            "is_toggle": False,
        },
        {
            "port_index": 6,
            "symbol": "Residual_listen",
            "name": "Residual listen",
            "min_val": 0.0,
            "max_val": 1.0,
            "default_val": 0.0,
            "current_val": 0.0,
            "is_toggle": True,
        },
        {
            "port_index": 7,
            "symbol": "bypass",
            "name": "Bypass",
            "min_val": 0.0,
            "max_val": 1.0,
            "default_val": 0.0,
            "current_val": 0.0,
            "is_toggle": True,
        },
    ]

    app = QApplication(sys.argv)
    window = MainWindow(samples)
    window.show()
    sys.exit(app.exec())
