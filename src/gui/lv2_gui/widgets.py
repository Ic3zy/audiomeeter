import sys
from PySide6.QtCore import Qt, Signal, QTimer, QMimeData, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QDrag, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSlider,
    QVBoxLayout,
    QWidget,
    QCheckBox,
    QSizePolicy,
    QFrame,
    QGraphicsDropShadowEffect,
    QScrollArea,
    QPushButton,
)

from core import Lv2Core

colors = {
    "plugin_wd_bg": "#033d43",
    "plugin_wd_bg_bottom": "#021f24",
    "plugin_border": "#0e5a63",
    "plugin_border_hover": "#2dd4c8",
    "plugin_label": "#d6f5f5",
    "sidebar_bg": "#07171a",
    "device_bg": "#0c2c31",
    "device_bg_hover": "#123a41",
    "device_bg_selected": "#0e5a63",
    "device_border_selected": "#2dd4c8",
    "device_text": "#cfeef0",
    "device_text_selected": "#ffffff",
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
        self.setCursor(Qt.CursorShape.PointingHandCursor)

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

        self.click_callback = None

    def on_click(self):
        print("clicked")
        if self.click_callback is not None:
            self.click_callback(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_click()

        super().mousePressEvent(event)


class CancelButton(QPushButton):
    def __init__(self, parent):
        super().__init__(parent)

        self.setFixedSize(70, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText("Cancel")

        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                color: #aaaaaa;
                font-size: 13px;
                font-weight: 500;
            }

            QPushButton:hover {
                background: rgba(255, 70, 70, 25);
                border-color: #a84444;
                color: #ff6666;
            }

            QPushButton:pressed {
                background: rgba(255, 70, 70, 45);
                border-color: #c44a4a;
                color: #ff4d4d;
            }
        """)


class PluginListContainer(QWidget):
    def __init__(self):
        super().__init__()

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setAlignment(Qt.AlignTop)

        self.content_layout = content_layout

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

        self.cancel_button = CancelButton(self)
        self.cancel_button.clicked.connect(self.cancel_clicked)

        self.cancel_button.move(
            self.width() - self.cancel_button.width() - 10,
            self.height() - self.cancel_button.height() - 10,
        )

        self.cancel_button_callback = None

        self.load_plugins()

    def set_plugins(self, plugin_infos):
        for param_info in plugin_infos:
            plugin_widget = Lv2PluginWidget(param_info)
            plugin_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            plugin_widget.click_callback = self.on_select_plugin
            self.content_layout.addWidget(plugin_widget)

    def load_plugins(self):
        Lv2Core.get_available_plugins_for_callback(self.set_plugins)

    def resizeEvent(self, event):
        super().resizeEvent(event)

        self.cancel_button.move(
            self.width() - self.cancel_button.width() - 10,
            self.height() - self.cancel_button.height() - 10,
        )

    def set_cancel_callback(self, callback):
        self.cancel_button_callback = callback

    def cancel_clicked(self):
        if self.cancel_button_callback is not None:
            self.cancel_button_callback()

        print("Cancel clicked")

    def on_select_plugin(self, plugin_widget):
        print(f"Selected plugin: {plugin_widget.param_name}")

        if instance := GeneralContainer.get():
            instance.restore()


class DeviceWidget(QWidget):
    clicked = Signal(str)

    def __init__(self, device_name):
        super().__init__()
        self.device_name = device_name
        self.selected = False
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(42)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.label = QLabel(device_name)
        self.label.setStyleSheet(f"""
            QLabel {{
                color: {colors["device_text"]};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(14, 0, 10, 0)
        layout.addWidget(self.label)

        self._apply_style()

    def _apply_style(self):
        if self.selected:
            self.setStyleSheet(f"""
                DeviceWidget {{
                    background-color: {colors["device_bg_selected"]};
                    border: none;
                    border-left: 3px solid {colors["device_border_selected"]};
                    border-radius: 4px;
                }}
            """)
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {colors["device_text_selected"]};
                    font-size: 12px;
                    font-weight: 600;
                    background: transparent;
                    border: none;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                DeviceWidget {{
                    background-color: {colors["device_bg"]};
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 4px;
                }}
                DeviceWidget:hover {{
                    background-color: {colors["device_bg_hover"]};
                }}
            """)
            self.label.setStyleSheet(f"""
                QLabel {{
                    color: {colors["device_text"]};
                    font-size: 12px;
                    font-weight: 500;
                    background: transparent;
                    border: none;
                }}
            """)

    def set_selected(self, value: bool):
        self.selected = value
        self._apply_style()

    def mousePressEvent(self, event):
        self.clicked.emit(self.device_name)
        super().mousePressEvent(event)


class DevicesContainer(QWidget):
    device_selected = Signal(str)

    def __init__(self, param_data):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(220)
        self.setStyleSheet(f"background-color: {colors['sidebar_bg']};")

        self.device_widgets = []

        outer_layout = QVBoxLayout(self)
        outer_layout.setSpacing(0)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("DEVICES")
        title.setStyleSheet(f"""
            QLabel {{
                color: {colors["plugin_label"]};
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1.5px;
                background: transparent;
                padding: 14px 14px 10px 14px;
                border: none;
            }}
        """)
        outer_layout.addWidget(title)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(
            f"background-color: {colors['plugin_border']}; max-height: 1px; border: none;"
        )
        outer_layout.addWidget(divider)

        content = QWidget()
        content.setAttribute(Qt.WA_StyledBackground, True)
        content.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(content)
        self.list_layout.setSpacing(4)
        self.list_layout.setContentsMargins(8, 10, 8, 10)
        self.list_layout.setAlignment(Qt.AlignTop)

        for name in param_data:
            dw = DeviceWidget(name)
            dw.clicked.connect(self._on_device_clicked)
            self.device_widgets.append(dw)
            self.list_layout.addWidget(dw)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {colors["plugin_border"]};
                border-radius: 4px;
                min-height: 24px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {colors["device_border_selected"]};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        outer_layout.addWidget(scroll)

        if self.device_widgets:
            self.device_widgets[0].set_selected(True)

    def _on_device_clicked(self, device_name):
        for dw in self.device_widgets:
            dw.set_selected(dw.device_name == device_name)
        self.device_selected.emit(device_name)


class ButtonWidget(QWidget):
    clicked = Signal()

    def __init__(self, text, width=None, height=42, font_size=12):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)

        self.setFixedHeight(height)
        if width:
            self.setFixedWidth(width)
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        else:
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self._pressed = False

        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet(f"""
            QLabel {{
                color: {colors["device_text"]};
                font-size: {font_size}px;
                font-weight: 600;
                letter-spacing: 0.3px;
                background: transparent;
                border: none;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 0, Qt.AlignCenter)

        self._apply_style()

    def _apply_style(self):
        bg = colors["device_bg_selected"] if self._pressed else colors["device_bg"]
        border = (
            colors["device_border_selected"]
            if self._pressed
            else colors["plugin_border"]
        )
        self.setStyleSheet(f"""
            ButtonWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            ButtonWidget:hover {{
                background-color: {colors["device_bg_hover"]};
                border: 1px solid {colors["device_border_selected"]};
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self._apply_style()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            was_pressed = self._pressed
            self._pressed = False
            self._apply_style()
            if was_pressed and self.rect().contains(event.pos()):
                self.clicked.emit()
        super().mouseReleaseEvent(event)


class SpinnerWidget(QWidget):
    def __init__(
        self,
        size=40,
        line_width=4,
        color=colors["device_border_selected"],
        track_color=colors["plugin_border"],
        speed=8,
    ):
        super().__init__()
        self.setFixedSize(size, size)
        self._angle = 0
        self._line_width = line_width
        self._color = QColor(color)
        self._track_color = QColor(track_color)
        self._speed = speed

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(16)  # ~60 FPS

    def _rotate(self):
        self._angle = (self._angle + self._speed) % 360
        self.update()

    def start(self):
        self._timer.start(16)

    def stop(self):
        self._timer.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(
            self._line_width, self._line_width, -self._line_width, -self._line_width
        )

        painter.translate(self.rect().center())
        painter.rotate(self._angle)
        painter.translate(-self.rect().center())

        bg_pen = QPen(self._track_color)
        bg_pen.setWidth(self._line_width)
        bg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 0, 360 * 16)

        fg_pen = QPen(self._color)
        fg_pen.setWidth(self._line_width)
        fg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(fg_pen)
        painter.drawArc(rect, 0, 100 * 16)


class DragHandle(QLabel):
    def __init__(self, owner_widget):
        super().__init__("⋮")
        self.owner_widget = owner_widget
        self.setFixedWidth(22)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.OpenHandCursor)
        self.setStyleSheet(f"""
            QLabel {{
                color: {colors["plugin_border_hover"]};
                font-size: 15px;
                font-weight: bold;
                background: transparent;
            }}
        """)
        self._press_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.position().toPoint()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is None:
            return

        moved = (event.position().toPoint() - self._press_pos).manhattanLength()
        if moved < QApplication.startDragDistance():
            return

        self._press_pos = None
        self.setCursor(Qt.ClosedHandCursor)
        self.owner_widget.start_drag()
        self.setCursor(Qt.OpenHandCursor)

    def mouseReleaseEvent(self, event):
        self._press_pos = None
        super().mouseReleaseEvent(event)


class ActivePluginWidget(QWidget):
    def __init__(self, param_info):
        super().__init__()
        self.param_info = param_info
        self.param_name = param_info["name"]
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.init_widget()

    def init_widget(self):
        outer = QHBoxLayout(self)
        outer.setSpacing(2)
        outer.setContentsMargins(2, 10, 14, 10)

        self.setFixedHeight(42)

        self.handle = DragHandle(self)
        outer.addWidget(self.handle)

        inner = QVBoxLayout()
        inner.setSpacing(6)
        inner.setContentsMargins(8, 0, 0, 0)

        label = QLabel(self.param_name)
        label.setStyleSheet(f"""
            QLabel {{
                color: {colors["plugin_label"]};
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.5px;
                background: transparent;
                border: none;
            }}
        """)
        inner.addWidget(label)
        outer.addLayout(inner, 1)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(18)
        self._shadow.setXOffset(0)
        self._shadow.setYOffset(3)
        self._shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(self._shadow)

        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(f"""
            ActivePluginWidget {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {colors["plugin_wd_bg"]},
                    stop:1 {colors["plugin_wd_bg_bottom"]}
                );
                border: 1px solid {colors["plugin_border"]};
                border-radius: 10px;
            }}
            ActivePluginWidget:hover {{
                border: 1px solid {colors["plugin_border_hover"]};
            }}
        """)

    def start_drag(self):
        drop_area = self.parent()
        if drop_area is None or not hasattr(drop_area, "handle_external_drop"):
            return

        mime = QMimeData()
        mime.setText(self.param_name)

        drag = QDrag(self)
        drag.setMimeData(mime)

        pixmap = self.grab()
        ghost = QPixmap(pixmap.size())
        ghost.fill(Qt.transparent)
        painter = QPainter(ghost)
        painter.setOpacity(0.75)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        drag.setPixmap(ghost)
        drag.setHotSpot(QPoint(20, pixmap.height() // 2))

        # self.setGraphicsEffect(None)
        self.hide()

        drop_area.start_reorder(self.param_name)
        drag.exec(Qt.MoveAction)
        drop_area.end_reorder()

        self.show()
        # self.setGraphicsEffect(self._shadow)


class PluginDropArea(QWidget):
    order_changed = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setAcceptDrops(True)

        self.layout_ = QVBoxLayout(self)
        self.layout_.setSpacing(10)
        self.layout_.setContentsMargins(20, 16, 20, 16)
        self.layout_.setAlignment(Qt.AlignTop)

        self.plugin_widgets = {}
        self._pending_index = None

        self._indicator = QFrame(self)
        self._indicator.setFixedHeight(3)
        self._indicator.setStyleSheet(f"""
            background-color: {colors["plugin_border_hover"]};
            border-radius: 1px;
        """)
        self._indicator.hide()

    def clear_plugins(self):
        for pw in list(self.plugin_widgets.values()):
            self.layout_.removeWidget(pw)
            pw.setParent(None)
            pw.deleteLater()

        self.plugin_widgets.clear()

    def set_plugins(self, plugin_infos):
        self.clear_plugins()

        for info in plugin_infos:
            self.add_plugin(info, emit_signal=False)

    def add_plugin(self, param_info, emit_signal=True):
        pw = ActivePluginWidget(param_info)
        pw.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.plugin_widgets[pw.param_name] = pw
        self.layout_.addWidget(pw)

        if emit_signal:
            self.order_changed.emit(self.current_order())

    def remove_plugin(self, param_name):
        pw = self.plugin_widgets.pop(param_name, None)

        if pw is None:
            return

        self.layout_.removeWidget(pw)

        pw.setParent(None)
        pw.deleteLater()

        self.order_changed.emit(self.current_order())

    def current_order(self):
        return list(self.plugin_widgets.keys())

    def is_empty(self):
        return len(self.plugin_widgets) == 0

    def start_reorder(self, param_name):
        self._pending_index = None

    def end_reorder(self):
        self._pending_index = None
        self._indicator.hide()

    def handle_external_drop(self):
        return True

    def _visible_plugin_widgets(self):
        result = []

        for i in range(self.layout_.count()):
            item = self.layout_.itemAt(i)
            w = item.widget()

            if w is not None and isinstance(w, ActivePluginWidget) and w.isVisible():
                result.append(w)

        return result

    def _index_for_y(self, y):
        widgets = self._visible_plugin_widgets()

        for i, w in enumerate(widgets):
            mid = w.y() + w.height() / 2
            if y < mid:
                return i

        return len(widgets)

    def dragEnterEvent(self, event):
        if (
            event.mimeData().hasText()
            and event.mimeData().text() in self.plugin_widgets
        ):
            event.acceptProposedAction()
            self._indicator.setFixedWidth(self.width() - 40)
            self._indicator.show()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not (
            event.mimeData().hasText()
            and event.mimeData().text() in self.plugin_widgets
        ):
            event.ignore()
            return

        pos_y = event.position().toPoint().y()
        index = self._index_for_y(pos_y)
        widgets = self._visible_plugin_widgets()

        if index >= len(widgets):
            target_y = widgets[-1].y() + widgets[-1].height() + 5 if widgets else 20
        else:
            target_y = widgets[index].y() - 6

        self._indicator.move(20, int(target_y))
        self._pending_index = index
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._indicator.hide()

    def dropEvent(self, event):
        self._indicator.hide()

        if not event.mimeData().hasText():
            event.ignore()
            return

        param_name = event.mimeData().text()
        pw = self.plugin_widgets.get(param_name)
        if pw is None:
            event.ignore()
            return

        target_index = self._pending_index
        if target_index is None:
            event.ignore()
            return

        self.layout_.removeWidget(pw)
        visible_after_removal = self._visible_plugin_widgets()
        insert_at = min(target_index, len(visible_after_removal))

        if insert_at >= len(visible_after_removal):
            self.layout_.addWidget(pw)
        else:
            ref_widget = visible_after_removal[insert_at]
            ref_layout_index = self.layout_.indexOf(ref_widget)
            self.layout_.insertWidget(ref_layout_index, pw)

        ordered = {}
        for i in range(self.layout_.count()):
            w = self.layout_.itemAt(i).widget()

            if isinstance(w, ActivePluginWidget):
                ordered[w.param_name] = w

        self.plugin_widgets = ordered

        self._pending_index = None
        event.acceptProposedAction()
        self.order_changed.emit(self.current_order())


class TitlBarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {colors['sidebar_bg']};")
        self.setFixedHeight(42)

        layout = QHBoxLayout(self)
        self.add_button = ButtonWidget("Add", width=50, font_size=11)
        self.add_button.clicked.connect(self.add_clicked)

        layout.addWidget(self.add_button, 0, Qt.AlignLeft)

        self.setLayout(layout)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

    def add_clicked(self):
        print("Add clicked")
        if instance := GeneralContainer.get():
            pl = PluginListContainer()
            # pl = PluginDropArea()
            # pl.set_plugins(plugin_infos)
            instance.clear()
            instance.add(pl)

            pl.set_cancel_callback(lambda: instance.restore())
        else:
            print("GeneralContainer instance not found")


class GeneralWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {colors['sidebar_bg']};")

        self.loading = True

        self.spinner = SpinnerWidget()
        self.label = QLabel("Loading, takes a few seconds...")

        self._outer_layout = QVBoxLayout(self)
        self._outer_layout.setContentsMargins(0, 0, 0, 0)
        self._outer_layout.setSpacing(0)

        self.widget = QWidget()
        self._layout = self.create_clean_layout()

        self.widget.setLayout(self._layout)
        self._outer_layout.addWidget(self.widget)

        self._layout.addStretch()
        self._layout.addWidget(self.spinner, 0, Qt.AlignCenter)
        self._layout.addWidget(self.label, 0, Qt.AlignCenter)
        self._layout.addStretch()

        self.ex_widget = None

    def create_clean_layout(self):
        layout = QVBoxLayout()

        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        return layout

    def start_loading(self):
        self.loading = True
        self.spinner.start()

    def stop_loading(self):
        self.loading = False
        self.spinner.stop()

    def add(self, widget):
        self._layout.addWidget(widget)

    def clear(self):
        current_widget = self.widget

        self._outer_layout.removeWidget(current_widget)
        current_widget.hide()
        current_widget.setParent(None)

        self.ex_widget = current_widget

        self.widget = QWidget()
        self._layout = self.create_clean_layout()

        self.widget.setLayout(self._layout)
        self._outer_layout.addWidget(self.widget)

        self.widget.show()

    def restore(self):
        if self.ex_widget is None:
            return

        current_widget = self.widget

        self._outer_layout.removeWidget(current_widget)
        current_widget.deleteLater()

        self.widget = self.ex_widget
        self.ex_widget = None

        self._outer_layout.addWidget(self.widget)

        self._layout = self.widget.layout()
        self.widget.show()


class GeneralContainer(QWidget):
    _general_container_instance = None

    @classmethod
    def get(cls):
        return cls._general_container_instance

    @classmethod
    def set_instance(cls, instance):
        cls._general_container_instance = instance

    def __init__(self):
        super().__init__()

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {colors['sidebar_bg']};")

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)

        self.title_bar = TitlBarWidget()
        self.g_widget = GeneralWidget()

        self.g_layout = QVBoxLayout(self.g_widget)
        self.g_layout.setSpacing(0)
        self.g_layout.setContentsMargins(0, 0, 0, 0)

        self.g_widget.setLayout(self.g_layout)

        self.layout.addWidget(self.title_bar)
        self.layout.addWidget(self.g_widget)

        self.setLayout(self.layout)

    def clear(self):
        self.g_widget.clear()

    def add(self, widget):
        self.g_widget.add(widget)

    def restore(self):
        self.g_widget.restore()


class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        l = ["A1", "A2", "A3"]

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.general_container = GeneralContainer()
        GeneralContainer.set_instance(self.general_container)

        self.devices_container = DevicesContainer(l)
        self.title_bar = TitlBarWidget()

        self.layout.addWidget(self.devices_container)

        self.main_layout.addLayout(self.layout)
        self.main_layout.addWidget(self.general_container, 0)

        self.setLayout(self.main_layout)


class MainWindow(QMainWindow):
    def __init__(self, param_data):
        super().__init__()
        self.setWindowTitle("AudioMeeter")
        self.central_widget = MainWidget()
        self.setCentralWidget(self.central_widget)


def run():
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


if __name__ == "__main__":
    run()
