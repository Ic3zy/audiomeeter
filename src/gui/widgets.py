from PySide6.QtWidgets import (
    QSlider, QStyleOptionSlider,
    QStyle, QWidget, QAbstractButton,
    QVBoxLayout, QHBoxLayout, QSizePolicy, QStyleOption
)
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PySide6.QtCore import Qt, QPropertyAnimation, Property, Signal, QEvent, QRect

from .styler import Styler
import math


# TODO: replace real IntelliPannel
class IntelliPannel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setFixedWidth(120)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        bg_color = "#132029"
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRect(self.rect())


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
        self.setFixedHeight(245)
        
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
        
        self.update_background_color(self.value())

    def add_status_change_callback(self, callback):
        if callback in self.status_change_callbacks:
            raise ValueError(f"Callback already added: {callback}")
        self.status_change_callbacks.append(callback)

    def update_background_color(self, value):
        new_color = "#ff5533" if value > 0 else "#71c49a"
        
        old_color = "#71c49a" if value > 0 else "#ff5533"
        
        current_qss = self.styleSheet()
        
        if current_qss:
            updated_qss = current_qss.replace(old_color, new_color)
            
            if updated_qss != current_qss:
                self.setStyleSheet(updated_qss)

    def on_slider_value_changed(self, value):
        if self.status_change_callbacks:
            for callback in self.status_change_callbacks:
                callback(value)

        print(f"{self.style_name} status: {value}")
        
        self.update_background_color(value)
        
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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            
            sr = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self
            )
            hr = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self
            )

            slider_length = sr.height() - hr.height()
            clicked_position = event.position().y() - sr.top() - hr.height() / 2
            
            ratio = 1.0 - (clicked_position / slider_length)
            new_value = int(self.minimum() + ratio * (self.maximum() - self.minimum()))
            
            new_value = max(self.minimum(), min(self.maximum(), new_value))
            self.setValue(new_value)
            
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            
            sr = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self
            )
            hr = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self
            )

            slider_length = sr.height() - hr.height()
            clicked_position = event.position().y() - sr.top() - hr.height() / 2
            
            ratio = 1.0 - (clicked_position / slider_length)
            new_value = int(self.minimum() + ratio * (self.maximum() - self.minimum()))
            
            new_value = max(self.minimum(), min(self.maximum(), new_value))
            self.setValue(new_value)
            
            event.accept()
        else:
            super().mouseMoveEvent(event)

class Mic_slider(Slider):
    def __init__(self):
        super().__init__()


class Hardware_slider(Slider):
    def __init__(self):
        super().__init__("hardware_slider")


class Circle_slider(QSlider):
    valueChanged = Signal(int)

    def __init__(self, min_val=-120, max_val=120, default_val=0, parent=None, in_circle_text=True):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.in_circle_text = in_circle_text

        self.current_value = default_val
        
        self.start_mouse_y = 0
        self.start_value = 0
        self.total_pixels_to_traverse = 200.0 
        
        self._slider_size = 100
        self.setFixedSize(self._slider_size, self._slider_size)

        styler_instance = Styler.instance()
        if styler_instance is None:
            raise ValueError("Styler instance not found.")
        
        styler_instance.set_style("circle_slider", self)

    @Property(int)
    def sliderSize(self):
        return self._slider_size

    @sliderSize.setter
    def sliderSize(self, size):
        self._slider_size = size
        self.setFixedSize(size, size)
        self.update()

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
        
        if self.current_value != 0:
            value_color = QColor("#71c49a")
        else:
            value_color = QColor("#607a89")


        palette = self.palette()
        bg_color = value_color
        active_color = palette.color(self.palette().ColorRole.Highlight)

        width, height = self.width(), self.height()
        size = min(width, height) - 22 
        cx, cy = width // 2, height // 2
        radius = size // 2

        line_width = 2

        bg_pen = QPen(bg_color, line_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawEllipse(cx - radius, cy - radius, size, size)

        total_range = self.max_val - self.min_val
        percentage = (self.current_value - self.min_val) / total_range
        
        span_angle_deg = percentage * 300

        knob_angle_deg = 90 - span_angle_deg - 211
        knob_angle_rad = math.radians(knob_angle_deg)

        knob_radius_offset = radius - 7

        knob_cx = cx + knob_radius_offset * math.cos(knob_angle_rad)
        knob_cy = cy - knob_radius_offset * math.sin(knob_angle_rad)

        knob_radius = 3
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(active_color)  
        
        painter.drawEllipse(
            int(knob_cx - knob_radius), 
            int(knob_cy - knob_radius), 
            knob_radius * 2, 
            knob_radius * 2
        )

        if self.in_circle_text:
            text_color = palette.color(self.palette().ColorRole.WindowText)
            painter.setPen(QPen(text_color))
            painter.setFont(QFont("Arial", 7, QFont.Weight.Bold))
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

        border_width = 1.5
        rect = self.rect().adjusted(border_width//2, border_width//2, -border_width//2, -border_width//2)
        radius = rect.height() / 3

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
        self.setFixedHeight(240)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(2)
        self.create()
    
    def addWidget(self, widget):
        self.layout.addWidget(widget)

    def create_object(self, text):
        if text == "air":
            return Air(4)
        else:
            return ToggleButton(text)

    def create(self):
        for text in self.map:
            btn = self.create_object(text)
            self.addWidget(btn)


class LEDVolumeMeter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._meter_width = 32
        self._meter_height = 220
        self.total_blocks = 40 
        
        self.current_value = 0.0
        
        self.setFixedSize(self._meter_width, self._meter_height)

        self._bg_panel = QColor("#161d20")
        self._border_panel = QColor("#222b2f")
        
        self._led_empty_low = QColor("#1a2222")
        self._led_empty_mid = QColor("#22281a") 
        self._led_empty_high = QColor("#2b1a1a") 

        self._led_full_low = QColor("#5b7a8c")
        self._led_full_mid = QColor("#4ade80")
        self._led_full_high = QColor("#ef4444")

        styler_instance = Styler.instance()
        if styler_instance:
            styler_instance.set_style("volume_meter", self)

    def setValue(self, val):
        self.current_value = max(0.0, min(1.0, val))
        self.update()

    @Property(int)
    def meterWidth(self): return self._meter_width
    @meterWidth.setter
    def meterWidth(self, w):
        self._meter_width = w
        self.setFixedSize(self._meter_width, self._meter_height)
        self.update()

    @Property(int)
    def meterHeight(self): return self._meter_height
    @meterHeight.setter
    def meterHeight(self, h):
        self._meter_height = h
        self.setFixedSize(self._meter_width, self._meter_height)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        panel_rect = self.rect()
        painter.setPen(QPen(self._border_panel, 1.5))
        painter.setBrush(QBrush(self._bg_panel))
        painter.drawRoundedRect(panel_rect.adjusted(1, 1, -1, -1), 4, 4)

        pad_left, pad_top, pad_right, pad_bottom = 4, 6, 4, 6
        inner_w = self.width() - (pad_left + pad_right)
        inner_h = self.height() - (pad_top + pad_bottom)
        
        col_w = (inner_w - 1) // 2 

        block_gap = 1
        block_h = (inner_h - (block_gap * (self.total_blocks - 1))) / self.total_blocks

        active_blocks_count = int(self.current_value * self.total_blocks)

        for i in range(self.total_blocks):
            y_pos = pad_top + inner_h - ((i + 1) * block_h + i * block_gap)
            
            progress_ratio = i / self.total_blocks
            
            if progress_ratio < 0.65:
                color_empty, color_full = self._led_empty_low, self._led_full_low
            elif progress_ratio < 0.85:
                color_empty, color_full = self._led_empty_mid, self._led_full_mid
            else:
                color_empty, color_full = self._led_empty_high, self._led_full_high

            is_active = i < active_blocks_count
            current_led_color = color_full if is_active else color_empty

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(current_led_color))

            painter.drawRect(pad_left, int(y_pos), col_w, int(block_h))
            painter.drawRect(pad_left + col_w + 1, int(y_pos), col_w, int(block_h))


class CompGate(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(2)

        self.comp = Circle_slider()
        self.gate = Circle_slider()

        self.layout.addWidget(self.comp)
        self.layout.addWidget(self.gate)

        self.setFixedWidth(120)
        self.setFixedHeight(70)


class Slider_buttons_div(QWidget):
    def __init__(self, parent=None, disable_led=False):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.setFixedHeight(255)
        # self.setFixedWidth(100)
        self.layout.setSpacing(0)

        self.r_toggle = Right_ToggleButtons()
        self.mic_slider = Mic_slider()

        if not disable_led:
            self.led_vol_meter = LEDVolumeMeter()

            self.layout.addWidget(self.led_vol_meter)

        self.layout.addWidget(self.mic_slider)
        self.layout.addWidget(self.r_toggle, alignment=Qt.AlignmentFlag.AlignBottom)


class Mic_container(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.setFixedWidth(160)
        self.layout.addWidget(IntelliPannel())
        self.layout.addWidget(CompGate())
        self.layout.addWidget(Slider_buttons_div())

class Mic_pannel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.setFixedWidth(440)

        self.m1 = Mic_container()
        self.m2 = Mic_container()
        self.m3 = Mic_container()

        self.layout.addWidget(self.m1)
        self.layout.addWidget(self.m2)
        self.layout.addWidget(self.m3)


# ---- virtual inputs ----
class Equalizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(130, 130)
        
        self.treble = Circle_slider(in_circle_text=False)
        self.mid = Circle_slider(in_circle_text=False)
        self.bass = Circle_slider(in_circle_text=False)

        for pot in [self.treble, self.mid, self.bass]:
            pot.sliderSize = 42
            pot.setParent(self)

        self.treble.move(0, 10)
        self.mid.move(30, 45)
        self.bass.move(0, 80)

        self.treble.valueChanged.connect(self.update)
        self.mid.valueChanged.connect(self.update)
        self.bass.valueChanged.connect(self.update)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QPen(QColor("#5b7a8c"))) 
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(QRect(-30, 0, self.width(), 20), Qt.AlignmentFlag.AlignCenter, "EQUALIZER")

        font_label = QFont("Arial", 8, QFont.Weight.Bold)
        font_value = QFont("Arial", 13, QFont.Weight.Bold)

        painter.setFont(font_label)
        painter.setPen(QPen(QColor("#4e616c")))
        painter.drawText(50, 26, "Treble")
        
        if self.treble.value() < 0:
            value_color = QColor("#71c49a")
        elif self.treble.value() > 0:
            value_color = QColor("#ff5533")
        else:
            value_color = QColor("#607a89")

        painter.setFont(font_value)
        painter.setPen(QPen(value_color))
        treble_val = f"{self.treble.value() / 10:.1f}"
        painter.drawText(55, 46, treble_val)

        if self.mid.value() < 0:
            value_color = QColor("#71c49a")
        elif self.mid.value() > 0:
            value_color = QColor("#ff5533")
        else:
            value_color = QColor("#607a89")

        painter.setFont(font_value)
        painter.setPen(QPen(value_color))
        mid_val = f"{self.mid.value() / 10:.1f}"
        print(len(mid_val))
        if len(mid_val) >= 4:
            pos = 0
        else:
            pos = 5
        painter.drawText(pos, 80, mid_val)

        bass_current = self.bass.value() / 10
        
        if self.bass.value() < 0:
            value_color = QColor("#71c49a")
        elif self.bass.value() > 0:
            value_color = QColor("#ff5533")
        else:
            value_color = QColor("#607a89")

        painter.setFont(font_value)
        painter.setPen(QPen(value_color))
        painter.drawText(55, 115, f"{bass_current:.1f}")

        painter.setFont(font_label)
        painter.setPen(QPen(QColor("#4e616c")))
        painter.drawText(55, 130, "Bass")

class Rl_Slider(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 50)

    def paintEvent(self, event):
        painter = QPainter(self)
        
        bg_color = "#132029"
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRect(self.rect())



class Virtual_input(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.setFixedHeight(465)
        self.setFixedWidth(120)

        self.eq = Equalizer()
        self.rl = Rl_Slider()
        self.sliders_container = Slider_buttons_div(disable_led=True)

        self.layout.addWidget(self.eq)
        self.layout.addWidget(self.rl)
        self.layout.addWidget(self.sliders_container)

class Virtual_input_panel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.setFixedHeight(465)
        self.setFixedWidth(200)

        self.sliders_1 = Virtual_input()
        self.sliders_2 = Virtual_input()

        self.layout.addWidget(self.sliders_1)
        self.layout.addWidget(self.sliders_2)

# ---- Hardware Output ----

class Hardware_sliders(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(15)

        self.sliders = []
        for _ in range(5):
            slider = Hardware_slider()
            self.sliders.append(slider)
            self.layout.addWidget(slider)
    
class Hardware_panel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.sliders = Hardware_sliders()
        self.layout.addWidget(self.sliders)


class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setFixedHeight(80)
        self.setFixedWidth(900)

    def paintEvent(self, event):
        painter = QPainter(self)
        
        bg_color = "#36495a"
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRect(self.rect())