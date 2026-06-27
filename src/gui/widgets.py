from PySide6.QtWidgets import QSlider, QStyleOptionSlider, QStyle, QWidget, QAbstractButton, QVBoxLayout, QSizePolicy
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PySide6.QtCore import Qt, QPropertyAnimation, Property, Signal, QEvent

from .styler import Styler
import math


# ----- sliders -----
class Slider(QSlider):
    def __init__(self, style_name="slider"):
        super().__init__(Qt.Orientation.Vertical)
        self.style_name = style_name
        self.status_change_callbacks = []

        self.setup_slider()

    def setup_slider(self):
        styler_instance = Styler.instance()
        if styler_instance is None:
            raise ValueError("Styler instance not found.")
        
        self.setMinimum(-60)
        self.setMaximum(12)
        self.setValue(0)

        if self.style_name is not None:
            styler_instance.set_style(self.style_name, self)
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)

        knob_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, 
            opt, 
            QStyle.SubControl.SC_SliderHandle, 
            self
        )

        self.setMinimumWidth(knob_rect.width())

        self.valueChanged.connect(self.on_slider_value_changed)

    def add_status_change_callback(self, callback):
        if callback in self.status_change_callbacks:
            raise ValueError(f"Callback already added: {callback}")
        
        self.status_change_callbacks.append(callback)


    def on_slider_value_changed(self, value):
        if self.status_change_callbacks:
            for callback in self.status_change_callbacks:
                callback(value)

        print(f"{self.style_name} status: {value}")
        self.update()


    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setValue(0)
        else:
            super().mouseDoubleClickEvent(event)

    
    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter()
        if painter.begin(self):
            try:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)

                opt = QStyleOptionSlider()
                self.initStyleOption(opt)

                knob_rect = self.style().subControlRect(
                    QStyle.ComplexControl.CC_Slider, 
                    opt, 
                    QStyle.SubControl.SC_SliderHandle, 
                    self
                )

                painter.setPen(QPen(QColor("#FFFFFF")))
                font = QFont("Arial", 9, QFont.Weight.Bold)
                painter.setFont(font)

                text = f"{self.value()}dB"
                painter.drawText(knob_rect, Qt.AlignmentFlag.AlignCenter, text)

            except Exception as e:
                print(f"paintEvent exception: {e}")

            finally:
                painter.end()


class Mic_slider(Slider):
    def __init__(self):
        super().__init__()


class Hardware_slider(Slider):
    def __init__(self):
        super().__init__("hardware_slider")



class Circle_slider(QSlider):
    valueChanged = Signal(int)

    def __init__(self, min_val=-120, max_val=120, default_val=0, parent=None):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.current_value = default_val
        
        self.start_mouse_y = 0
        self.start_value = 0
        
        self.total_pixels_to_traverse = 200.0 
        
        self.setMinimumSize(100, 100)

        styler_instance = Styler.instance()
        if styler_instance is None:
            raise ValueError("Styler instance not found.")
        
        self.setStyleSheet(styler_instance["circle_slider"])

    def value(self):
        return self.current_value

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setValue(0)
        else:
            super().mouseDoubleClickEvent(event)

    def setValue(self, value):
        value = max(self.min_val, min(self.max_val, value))
        if self.current_value != value:
            self.current_value = value
            self.valueChanged.emit(self.current_value)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        palette = self.palette()
        bg_color = palette.color(self.backgroundRole())
        active_color = palette.color(self.palette().ColorRole.Highlight)

        width, height = self.width(), self.height()
        size = min(width, height) - 22 
        cx, cy = width // 2, height // 2
        radius = size // 2

        line_width = 6

        bg_pen = QPen(bg_color, line_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawEllipse(cx - radius, cy - radius, size, size)

        total_range = self.max_val - self.min_val
        percentage = (self.current_value - self.min_val) / total_range
        
        span_angle_deg = percentage * 300


        knob_angle_deg = 90 - span_angle_deg - 211
        knob_angle_rad = math.radians(knob_angle_deg)

        knob_radius_offset = radius - 10

        knob_cx = cx + knob_radius_offset * math.cos(knob_angle_rad)
        knob_cy = cy - knob_radius_offset * math.sin(knob_angle_rad)


        knob_radius = 4
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(active_color)  
        
        painter.drawEllipse(
            int(knob_cx - knob_radius), 
            int(knob_cy - knob_radius), 
            knob_radius * 2, 
            knob_radius * 2
        )

        text_color = palette.color(self.palette().ColorRole.WindowText)
        painter.setPen(QPen(text_color))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        text = f"{self.current_value/10:.1f}"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_mouse_y = event.position().y()
            self.start_value = self.current_value

    def mouseMoveEvent(self, event):
        if self.signalsBlocked():
            return
            
        total_delta_y = event.position().y() - self.start_mouse_y
        
        pixel_ratio = -total_delta_y / self.total_pixels_to_traverse
        
        total_range = self.max_val - self.min_val
        
        value_change = pixel_ratio * total_range
        new_value = int(self.start_value + value_change)
        
        self.setValue(new_value)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.releaseMouse()


# ---- togle button ----
class ToggleButton(QAbstractButton):
    stateChanged = Signal(bool)

    def __init__(self, text=None, parent=None):
        super().__init__(parent)
        self.button_text = text
        self.setCheckable(True)
        self.setSizePolicy(self.sizePolicy().Policy.Fixed, self.sizePolicy().Policy.Fixed)

        self._btn_width = 60
        self._btn_height = 28
        self._font_size = 9
        self.setFixedSize(self._btn_width, self._btn_height)

        self._bg_color = QColor("#1c2529")
        self._outline_off = QColor("#3d4b52")
        self._outline_on = QColor("#3a7899")
        self._text_off = QColor("#a0a0a0")
        self._text_on = QColor("#ffffff")

        self.clicked.connect(lambda: self.stateChanged.emit(self.isChecked()))

        from .styler import Styler 
        styler_instance = Styler.instance()
        if styler_instance:
            styler_instance.set_style("toggle_button", self)

    @Property(int)
    def btnWidth(self): return self._btn_width
    @btnWidth.setter
    def btnWidth(self, w):
        self._btn_width = w
        self.setFixedSize(self._btn_width, self._btn_height) 
        self.update()

    @Property(int)
    def btnHeight(self): return self._btn_height
    @btnHeight.setter
    def btnHeight(self, h):
        self._btn_height = h
        self.setFixedSize(self._btn_width, self._btn_height) 
        self.update()

    @Property(int)
    def fontSize(self): return self._font_size
    @fontSize.setter
    def fontSize(self, size):
        self._font_size = size
        self.update()

    @Property(QColor)
    def bgColor(self): return self._bg_color
    @bgColor.setter
    def bgColor(self, c): self._bg_color = c; self.update()

    @Property(QColor)
    def outlineOff(self): return self._outline_off
    @outlineOff.setter
    def outlineOff(self, c): self._outline_off = c; self.update()

    @Property(QColor)
    def outlineOn(self): return self._outline_on
    @outlineOn.setter
    def outlineOn(self, c): self._outline_on = c; self.update()

    @Property(QColor)
    def outlineHover(self): return self._outline_hover
    @outlineHover.setter
    def outlineHover(self, c): self._outline_hover = c; self.update()

    @Property(QColor)
    def textOff(self): return self._text_off
    @textOff.setter
    def textOff(self, c): self._text_off = c; self.update()

    @Property(QColor)
    def textOn(self): return self._text_on
    @textOn.setter
    def textOn(self, c): self._text_on = c; self.update()


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.isChecked():
            current_outline = self._outline_on
        else:
            current_outline = self._outline_off

        current_text_color = self._text_on if self.isChecked() else self._text_off

        border_width = 2
        rect = self.rect().adjusted(border_width//2, border_width//2, -border_width//2, -border_width//2)
        radius = rect.height() / 4

        pen = QPen(current_outline, border_width)
        painter.setPen(pen)
        painter.setBrush(QBrush(self._bg_color))
        painter.drawRoundedRect(rect, radius, radius)

        painter.setPen(QPen(current_text_color))
        painter.setFont(QFont("Arial", self._font_size, QFont.Weight.Bold))
        
        if self.button_text:
            text = self.button_text
        else:
            text = "ON" if self.isChecked() else "OFF"
            
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)


class Air(QWidget):
    def __init__(self, height=15, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(height)


class Right_ToggleButtons(QWidget):
    def __init__(self, mono="Mono"):
        super().__init__()
        self.map = [
            "A1",
            "A2",
            "A3",
            "air",
            "B1",
            "B2",
            "air",
            mono,
            "air",
            "Solo",
            "Mute"
        ]
        self.layout = QVBoxLayout(self)
        self.create()
    
    def addWidget(self, widget):
        self.layout.addWidget(widget)

    def create_object(self, text):
        if text == "air":
            return Air(15)
        else:
            return ToggleButton(text)

    def create(self):
        for text in self.map:
            btn = self.create_object(text)
            self.addWidget(btn)

