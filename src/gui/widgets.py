import asyncio
import math

from PySide6.QtCore import (Property, QEvent, QPoint, QPropertyAnimation, QRect,
                            Signal, Qt)
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPolygon, QPen
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog,
                               QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QMainWindow, QPushButton,
                               QSizePolicy, QSlider, QStyle, QStyleOption,
                               QStyleOptionSlider, QVBoxLayout, QWidget)

from .styler import Styler
from base import Ctx
from core import DevicesManager

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


        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QPen(QColor("#5b7a8c")))

        painter.setFont(self.font())

        text_rect = QRect(0, 10, self.width(), 20) 

        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "To be continued...")


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

        if self.style_name == "hardware_slider":
            self.setFixedHeight(171)
        else:
            self.setFixedHeight(245)

        self.setFixedWidth(0)
        
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
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

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

                groove_rect = self.style().subControlRect(
                    QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self
                )

                add_page_top = knob_rect.bottom()
                add_page_bottom = groove_rect.bottom()
                add_page_height = add_page_bottom - add_page_top


                if add_page_height > 5: 
                    painter.save()

                    clip_rect = QRect(groove_rect.left(), add_page_top, groove_rect.width(), add_page_height)
                    painter.setClipRect(clip_rect)

                    fixed_font = QFont("Segoe UI")
                    if self.style_name == "hardware_slider":
                        fixed_font.setWeight(QFont.Weight.DemiBold)

                        fixed_font.setPointSize(9)
                    else:
                        fixed_font.setWeight(QFont.Weight.Bold)

                        fixed_font.setPointSize(11)


                    painter.setFont(fixed_font)
                    color = "#3d966a" if self.value() <= 0 else "#a01400"
                    painter.setPen(QPen( QColor(color) ))

                    fixed_text = "Faber Gain"

                    center = groove_rect.center()
                    painter.translate(center.x(), center.y())

                    painter.rotate(-90)

                    text_width = painter.fontMetrics().horizontalAdvance(fixed_text)

                    if self.style_name == "hardware_slider":
                        fixed_text_rect = QRect(
                            -text_width // 2 + -30,
                            -groove_rect.height() // 2, 
                            text_width,
                            groove_rect.height()
                        )

                    else:
                        fixed_text_rect = QRect(
                            -text_width // 2 + -60,
                            -groove_rect.height() // 2, 
                            text_width,
                            groove_rect.height()
                        )



                    painter.drawText(fixed_text_rect, Qt.AlignmentFlag.AlignCenter, fixed_text)

                    painter.resetTransform()
                    painter.restore()

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

        self.status_change_callbacks = []

        self.valueChanged.connect(self.on_slider_value_changed)

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

    def on_slider_value_changed(self, value):
        if self.status_change_callbacks:
            for callback in self.status_change_callbacks:
                callback(value)

    def add_status_change_callback(self, callback):
        if callback in self.status_change_callbacks:
            raise ValueError(f"Callback already added: {callback}")
        
        self.status_change_callbacks.append(callback)

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
        self.clicked.connect(self.on_state_changed)

        self.status_change_callbacks = []

        styler_instance = Styler.instance()
        if styler_instance:
            styler_instance.set_style("toggle_button", self)

    def on_state_changed(self, state):
        for callback in self.status_change_callbacks:
            callback(state)
    
    def add_status_change_callback(self, callback):
        if callback in self.status_change_callbacks:
            raise ValueError(f"Callback already added: {callback}")

        self.status_change_callbacks.append(callback)
        

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

class Right_ToggleButtons(QWidget):
    def __init__(self, mono="Mono", slider_number=None):
        if  slider_number is None:
            raise ValueError("slider_number cannot be None")

        self.slider_number = slider_number

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
            ctx_name = f"s_{self.slider_number}_{text}"
            
            def callback(state, c=ctx_name):
                print(f"callback: {c}")
                Ctx[c] = state

            def ctx_callback(b=btn, c=ctx_name):
                b.blockSignals(True)
            
                if hasattr(b, "setChecked"):
                    b.setChecked(Ctx[c])
                    
                b.blockSignals(False)
            
            Ctx.add_callback(ctx_name, ctx_callback)

            if hasattr(btn, "stateChanged"):
                btn.stateChanged.connect(callback)
            
            self.addWidget(btn)


class CompGate(QWidget):
    def __init__(self, parent=None, slider_number=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(2)

        self.comp = Circle_slider()
        def comp_callback(value):
            ctx_name = f"s_{slider_number}_Comp"
            Ctx[ctx_name] = value
        
        def comp_ctx_callback():
            comp_value = Ctx[f"s_{slider_number}_Comp"]
            self.comp.setValue(comp_value)
            self.comp.update()

        Ctx.add_callback(f"s_{slider_number}_Comp", comp_ctx_callback)
        self.comp.add_status_change_callback(comp_callback)
        
        self.gate = Circle_slider()
        def gate_callback(value):
            ctx_name = f"s_{slider_number}_Gate"
            Ctx[ctx_name] = value

        def gate_ctx_callback():
            gate_value = Ctx[f"s_{slider_number}_Gate"]
            self.gate.setValue(gate_value)
            self.gate.update()
        
        Ctx.add_callback(f"s_{slider_number}_Gate", gate_ctx_callback)

        self.gate.add_status_change_callback(gate_callback)

        self.layout.addWidget(self.comp)
        self.layout.addWidget(self.gate)

        self.setFixedWidth(120)
        self.setFixedHeight(70)


class Slider_buttons_div(QWidget):
    def __init__(self, parent=None, disable_led=False, slider_number=None):
        if slider_number is None:
            raise ValueError("slider_number cannot be None")
        
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.setFixedHeight(255)
        self.layout.setSpacing(0)

        self.r_toggle = Right_ToggleButtons(slider_number=slider_number)
        self.mic_slider = Mic_slider()
        def mic_callback(value):
            ctx_name = f"s_sl_{slider_number}"
            Ctx[ctx_name] = value

        def mic_ctx_callback():
            mic_value = Ctx[f"s_sl_{slider_number}"]
            self.mic_slider.setValue(mic_value)
            self.mic_slider.update()
        
        Ctx.add_callback(f"s_sl_{slider_number}", mic_ctx_callback)
        self.mic_slider.add_status_change_callback(mic_callback)

        if not disable_led:
            self.led_vol_meter = LEDVolumeMeter()

            self.layout.addWidget(self.led_vol_meter)

        self.layout.addWidget(self.mic_slider)
        self.layout.addWidget(self.r_toggle, alignment=Qt.AlignmentFlag.AlignBottom)


class Mic_container(QWidget):
    def __init__(self, parent=None, slider_number=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.setFixedWidth(160)
        self.layout.addWidget(IntelliPannel())
        self.layout.addWidget(CompGate(slider_number=slider_number))
        self.layout.addWidget(Slider_buttons_div(slider_number=slider_number))

class Mic_pannel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.setFixedWidth(440)

        self.m1 = Mic_container(slider_number=1)
        self.m2 = Mic_container(slider_number=2)
        self.m3 = Mic_container(slider_number=3)

        self.layout.addWidget(self.m1)
        self.layout.addWidget(self.m2)
        self.layout.addWidget(self.m3)


# ---- virtual inputs ----

class VirtualInputLedVM(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._meter_width = 15
        self._meter_height = 54
        self.current_value = 0.0
        
        self.setFixedSize(self._meter_width, self._meter_height)

        self._bg_panel = QColor("#0a0d0f")
        self._border_panel = QColor("#161d20")

        self._led_empty_low = QColor("#121b1c")   
        self._led_empty_mid = QColor("#111c14")   
        self._led_empty_high = QColor("#1c1212")  

        self._led_full_low = QColor("#5bc0be")    
        self._led_full_mid = QColor("#00e676")    
        self._led_full_high = QColor("#ff3333")  
        
        self._live_task = None
        self._anim_task = None

    async def _live_loop(self):
        is_plussed = False
        while True:
            if self.current_value <= 0.1:
                await asyncio.sleep(0.05)
                continue

            self.current_value += 0.04 if not is_plussed else -0.04
            is_plussed = not is_plussed
            self.update()
            await asyncio.sleep(0.1)

    async def _animate(self, end):
        start = self.current_value
        if abs(start - end) < 0.001:
            return

        reverse = start > end
        last = start

        while True:
            if reverse:
                last -= 0.07
                if last <= end:
                    last = end
                    break
            else:
                last += 0.07
                if last >= end:
                    last = end
                    break

            self.current_value = last
            self.update()
            await asyncio.sleep(0.025)

        self.current_value = end
        self.update()

    def db_to_percent(self, db):
        return (db + 100) / 112

    def setValue(self, val):
        end = self.db_to_percent(val)

        if self._anim_task and not self._anim_task.done():
            self._anim_task.cancel()

        if self._live_task is None or self._live_task.done():
            self._live_task = asyncio.create_task(self._live_loop())
        
        self._anim_task = asyncio.create_task(self._animate(end))


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        panel_rect = self.rect()
        painter.setPen(QPen(self._border_panel, 1))
        painter.setBrush(QBrush(self._bg_panel))
        painter.drawRoundedRect(panel_rect.adjusted(0, 0, -1, -1), 3, 3)

        offset_x = 3
        offset_y = 3

        active_rows_count = int(self.current_value * 27)

        for i in range(24):
            y_pos = offset_y + 46 - (i * 2)

            if i < 12:    
                color_empty, color_full = self._led_empty_low, self._led_full_low
            elif i < 18:  
                color_empty, color_full = self._led_empty_mid, self._led_full_mid
            else:         
                color_empty, color_full = self._led_empty_high, self._led_full_high

            is_active = i < active_rows_count

            current_led_color = color_full if is_active else color_empty

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(current_led_color))

            for j in range(5):
                x_pos = offset_x + (j * 2)
                painter.drawRect(x_pos, y_pos, 1, 1)

class Equalizer(QWidget):
    def __init__(self, parent=None, slider_number=None):
        if slider_number is None:
            raise ValueError("slider_number cannot be None")
        
        super().__init__(parent)
        self.setFixedSize(130, 130)
        
        self.treble = Circle_slider(in_circle_text=False)
        self.mid = Circle_slider(in_circle_text=False)
        self.bass = Circle_slider(in_circle_text=False)

        for pot in [self.treble, self.mid, self.bass]:
            pot.sliderSize = 42
            pot.setParent(self)

        self.treble.move(0, 10)
        def treble_callback(value):
            ctx_name = f"s_{slider_number}_Treble"
            Ctx[ctx_name] = value
        
        def treble_ctx_callback():
            treble_value = Ctx[f"s_{slider_number}_Treble"]
            self.treble.setValue(treble_value)
            self.treble.update()
        
        Ctx.add_callback(f"s_{slider_number}_Treble", treble_ctx_callback)
        self.treble.add_status_change_callback(treble_callback)

        self.mid.move(30, 45)
        def mid_callback(value):
            ctx_name = f"s_{slider_number}_Mid"
            Ctx[ctx_name] = value
        
        def mid_ctx_callback():
            mid_value = Ctx[f"s_{slider_number}_Mid"]
            self.mid.setValue(mid_value)
            self.mid.update()
        
        Ctx.add_callback(f"s_{slider_number}_Mid", mid_ctx_callback)
        self.mid.add_status_change_callback(mid_callback)

        self.bass.move(0, 80)
        def bass_callback(value):
            ctx_name = f"s_{slider_number}_Bass"
            Ctx[ctx_name] = value

        def bass_ctx_callback():
            bass_value = Ctx[f"s_{slider_number}_Bass"]
            self.bass.setValue(bass_value)
            self.bass.update()
        
        Ctx.add_callback(f"s_{slider_number}_Bass", bass_ctx_callback)
        self.bass.add_status_change_callback(bass_callback)

        self.treble.valueChanged.connect(self.update)
        self.mid.valueChanged.connect(self.update)
        self.bass.valueChanged.connect(self.update)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(QPen(QColor("#5b7a8c"))) 
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(QRect(-30, 0, self.width(), 10), Qt.AlignmentFlag.AlignCenter, "EQUALIZER")

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
        self.setFixedSize(65, 55)

    def paintEvent(self, event):
        painter = QPainter(self)
        
        bg_color = "#132029"
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRect(self.rect())

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#5b7a8c")))
        font = QFont("Arial", 7, QFont.Weight.Bold)
        self.setFont(font)
        painter.setFont(self.font())
        text_rect = QRect(0, 8, self.width(), 25) 
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "To be \ncontinued")


class Virtual_input(QWidget):
    def __init__(self, parent=None, slider_number=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.setFixedHeight(465)
        self.setFixedWidth(120)

        self.eq = Equalizer(slider_number=slider_number+3)
        self.rl = Rl_Slider(self)

        self.led_vm = VirtualInputLedVM(self)
        name = "input_main" if slider_number == 1 else "input_aux"
    

        Ctx.add_callback(name, lambda: self.led_vm.setValue(Ctx[name]))

        self.rl_air = Air(height=50)
        self.sliders_container = Slider_buttons_div(disable_led=True, slider_number=slider_number+3)

        self.rl.move(15, 155)
        self.led_vm.move(85, 156)

        self.layout.addWidget(self.eq)
        self.layout.addWidget(self.rl_air)
        self.layout.addWidget(self.sliders_container)

class Virtual_input_panel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.setFixedHeight(465)
        self.setFixedWidth(200)

        self.sliders_1 = Virtual_input(slider_number=1)
        self.sliders_2 = Virtual_input(slider_number=2)

        self.layout.addWidget(self.sliders_1)
        self.layout.addWidget(self.sliders_2)




class Cassette_player(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(150)
        self.setFixedWidth(240)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        
        bg_color = "#132029"
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRect(self.rect())

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#5b7a8c")))
        painter.setFont(self.font())

        text_rect = QRect(0, 10, self.width(), 20) 
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "To be continued...")



# ---- Hardware Output ----

class HardwareLedVM(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._meter_width = 18
        self._meter_height = 134
        self.current_value = 0.0
        
        self.setFixedSize(self._meter_width, self._meter_height)

        self._bg_panel = QColor("#0a0d0f")
        self._border_panel = QColor("#161d20")

        self._led_empty_low = QColor("#121b1c")   
        self._led_empty_mid = QColor("#111c14")   
        self._led_empty_high = QColor("#1c1212")  

        self._led_full_low = QColor("#5bc0be")    
        self._led_full_mid = QColor("#00e676")    
        self._led_full_high = QColor("#ff3333")

        self._live_task = None
        self._anim_task = None

    async def _live_loop(self):
        is_plussed = False
        while True:
            if self.current_value <= 0.1:
                await asyncio.sleep(0.1)
                continue

            self.current_value += 0.02 if not is_plussed else -0.02
            is_plussed = not is_plussed
            self.update()
            await asyncio.sleep(0.1)

    async def _animate(self, end):
        start = self.current_value
        if abs(start - end) < 0.001:
            return

        reverse = start > end
        last = start

        while True:
            if reverse:
                last -= 0.07
                if last <= end:
                    last = end
                    break
            else:
                last += 0.07
                if last >= end:
                    last = end
                    break

            self.current_value = last
            self.update()
            await asyncio.sleep(0.025)

        self.current_value = end
        self.update()

    def db_to_percent(self, db):
        return (db + 100) / 112

    def setValue(self, val):
        end = self.db_to_percent(val)

        if self._anim_task and not self._anim_task.done():
            self._anim_task.cancel()

        if self._live_task is None or self._live_task.done():
            self._live_task = asyncio.create_task(self._live_loop())
        
        self._anim_task = asyncio.create_task(self._animate(end))

    # TODO: optimize 
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        panel_rect = self.rect()
        painter.setPen(QPen(self._border_panel, 1))
        painter.setBrush(QBrush(self._bg_panel))
        painter.drawRoundedRect(panel_rect.adjusted(0, 0, -1, -1), 3, 3)

        offset_x = 3
        offset_y = 3

        active_rows_count = int(self.current_value * 64)

        for i in range(64):
            y_pos = offset_y + 126 - (i * 2)

            if i < 35:    
                color_empty, color_full = self._led_empty_low, self._led_full_low
            elif i < 57:  
                color_empty, color_full = self._led_empty_mid, self._led_full_mid
            else:         
                color_empty, color_full = self._led_empty_high, self._led_full_high

            is_active = i < active_rows_count
            current_led_color = color_full if is_active else color_empty

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(current_led_color))

            for j in range(7):
                x_pos = offset_x + (j * 2)
                painter.drawRect(x_pos, y_pos, 1, 1)


class Hardware_buttons(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        pass

class H_Slider(QWidget):
    def __init__(self, parent=None, slider_number=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(-10, -10, -10, -10)
        # self.setFixedWidth(5)
        self.setFixedHeight(190)

        self.slider = Slider("hardware_slider")
        def slider_callback(value):
            ctx_name = f"s_sl_{slider_number}"
            Ctx[ctx_name] = value
        
        def slider_ctx_callback():
            slider_value = Ctx[f"s_sl_{slider_number}"]
            self.slider.setValue(slider_value)
            self.slider.update()
        
        Ctx.add_callback(f"s_sl_{slider_number}", slider_ctx_callback)
        self.slider.add_status_change_callback(slider_callback)

        self.led_vol_meter = HardwareLedVM()
        # Ctx[f"s_led_{slider_number}"] = 0
        def led_callback():
            value = Ctx[f"s_led_{slider_number}"]
            self.led_vol_meter.setValue(value)
        Ctx.add_callback(f"s_led_{slider_number}", led_callback)

        self.layout.addWidget(self.led_vol_meter)
        self.layout.addWidget(self.slider)

class ChannelControls(QWidget):
    def __init__(self, parent=None, slider_number=None):
        if slider_number is None:
            raise ValueError("slider_number cannot be None")
        
        super().__init__(parent)
        self.setFixedWidth(60) 
        self.setFixedHeight(72)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 0, 0, 0)

        self.mono = ToggleButton("Mono")
        def mono_callback(state):
            ctx_name = f"s_{slider_number}_Mono"
            Ctx[ctx_name] = state
        
        def mono_ctx_callback():
            mono_value = Ctx[f"s_{slider_number}_Mono"]
            self.mono.setChecked(mono_value)
            self.mono.update()
        
        Ctx.add_callback(f"s_{slider_number}_Mono", mono_ctx_callback)
        self.mono.add_status_change_callback(mono_callback)

        self.eq = ToggleButton("EQ")
        def eq_callback(state):
            ctx_name = f"s_{slider_number}_Eq"
            Ctx[ctx_name] = state
        
        def eq_ctx_callback():
            eq_value = Ctx[f"s_{slider_number}_Eq"]
            self.eq.setChecked(eq_value)
            self.eq.update()
        
        Ctx.add_callback(f"s_{slider_number}_Eq", eq_ctx_callback)
        self.eq.add_status_change_callback(eq_callback)

        self.mute = ToggleButton("Mute")
        def mute_callback(state):
            ctx_name = f"s_{slider_number}_Mute"
            Ctx[ctx_name] = state
        
        def mute_ctx_callback():
            mute_value = Ctx[f"s_{slider_number}_Mute"]
            self.mute.setChecked(mute_value)
            self.mute.update()
        
        Ctx.add_callback(f"s_{slider_number}_Mute", mute_ctx_callback)
        self.mute.add_status_change_callback(mute_callback)

        self.layout.addWidget(self.mono)
        self.layout.addWidget(self.eq)
        self.layout.addWidget(self.mute)

class Hardware_slider(QWidget):
    def __init__(self, parent=None, slider_number=None):
        super().__init__(parent)
        self.setFixedWidth(74)
        self.setFixedHeight(290)
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.slider = H_Slider(slider_number=slider_number)

        self.buttons = ChannelControls(slider_number=slider_number)

        self.layout.addWidget(Air(height=40))

        self.layout.addWidget(self.buttons)
        self.layout.addWidget(self.slider)


class H_Slider_container(QWidget):
    def __init__(self, parent=None, slider_number=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setFixedWidth(290)
        self.setFixedHeight(290)
        
        self.slider = Hardware_slider(slider_number=slider_number)
        self.layout.addWidget(self.slider)


class Hardware_sliders(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(290)
        self.setFixedHeight(290)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 10, 0)

        self.sliders = []
        for _ in range(5):
            slider = H_Slider_container(slider_number=_+6)
            self.sliders.append(slider)
            self.layout.addWidget(slider)


class Hardware_panel(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(Cassette_player(), alignment=Qt.AlignmentFlag.AlignHCenter)
        self.sliders = Hardware_sliders()
        self.layout.addWidget(self.sliders)

# ---- select hardware out ----
class AudioDeviceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ses Cihazı Seçimi")
        self.setFixedSize(320, 280)
        
        self.selected_device = None

        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e24;
                border: 1px solid #323242;
            }
            QLabel {
                color: #a0a0b8;
                font-family: 'Arial';
                font-size: 11px;
            }
            QListWidget {
                background-color: #121216;
                border: 1px solid #2d2d3d;
                border-radius: 6px;
                color: #ffffff;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background-color: #252530;
                color: #00f2fe;
            }
            QListWidget::item:selected {
                background-color: #0575e6;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton {
                background-color: #252533;
                color: #ffffff;
                border: 1px solid #3d3d52;
                border-radius: 4px;
                padding: 7px 15px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0575e6;
                border-color: #00f2fe;
            }
        """)

        layout = QVBoxLayout()
        
        self.label = QLabel("Select Output Device", self)
        layout.addWidget(self.label)
        
        self.device_list = QListWidget(self)
        layout.addWidget(self.device_list)
        
        self.load_devices()

        btn_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.select_btn = QPushButton("Select", self)
        self.select_btn.clicked.connect(self.accept_selection)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.select_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)

    def load_devices(self):
        devices = DevicesManager.get_physical_sinks()
        
        for dev in devices:
            item = QListWidgetItem(dev.description)
            item.setData(Qt.UserRole, dev.index)
            self.device_list.addItem(item)
            
        if self.device_list.count() > 0:
            self.device_list.setCurrentRow(0)

    def index_to_device_id(self, index):
        for dev in DevicesManager.get_physical_sinks():
            if dev.index == index:
                return dev.name

    def index_to_name(self, index):
        for dev in DevicesManager.get_physical_sinks():
            if dev.index == index:
                return dev.description

    def accept_selection(self):
        current_item = self.device_list.currentItem()
        if current_item:
            self.selected_device = current_item.data(Qt.UserRole)
            self.accept()


# ---- title bar ----
class Select_hardware_output_buttons(QWidget):
    def __init__(self, parent=None, slider_number=1):
        super().__init__(parent)
        self.slider_number = slider_number
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.setFixedSize(25, 35) 
        self.text = f"A{slider_number}"

    def clear_other(self, name):
        others = []
        for _ in range(3):
            ctx_name = f"H_Out_A{_+1}"
            if Ctx[ctx_name] == name:
                Ctx[ctx_name] = ""
        
        return others

    def on_widget_clicked(self):
        popup = AudioDeviceDialog(self)
        if popup.exec() == QDialog.Accepted:
            device_name = popup.index_to_name(popup.selected_device)
            device_id = popup.index_to_device_id(popup.selected_device)

            ctx_name = f"H_Out_A{self.slider_number}"
            ctx_r_name = f"H_Out_A{self.slider_number}_id"

            self.clear_other(device_name)

            if Ctx[ctx_name] == device_name:
                Ctx[ctx_name] = ""
                Ctx[ctx_r_name] = None
                return
            
            Ctx[ctx_r_name] = device_id
            Ctx[ctx_name] = device_name
        else:
            print("\ncancel.\n")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_widget_clicked()

        event.accept()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w_rect = self.rect()

        border_pen = QPen(QColor("#607a89"), 1)
        bg_brush = QBrush(QColor("#3d5267")) 
        
        painter.setPen(border_pen)
        painter.setBrush(bg_brush)
        
        btn_rect = QRect(w_rect.left() + 1, w_rect.top() + 1, w_rect.width() - 2, w_rect.height() - 2)
        painter.drawRect(btn_rect)

        top_font = QFont("Arial")
        top_font.setPixelSize(11)
        top_font.setBold(True)
        painter.setFont(top_font)
        painter.setPen(QPen(QColor("#eef2f5"))) 
        
        text_rect = QRect(btn_rect.left(), btn_rect.top() + 2, btn_rect.width(), 16)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.text)

        arrow_pen = QPen(QColor("#d1dbe3"), 1)
        arrow_brush = QBrush(QColor("#d1dbe3"))
        painter.setPen(arrow_pen)
        painter.setBrush(arrow_brush)
        
        center_x = btn_rect.center().x()
        arrow_top_y = text_rect.bottom() + 1
        
        points = [
            QPoint(center_x - 3, arrow_top_y),
            QPoint(center_x + 3, arrow_top_y),
            QPoint(center_x, arrow_top_y + 3)
        ]
        
        painter.drawPolygon(QPolygon(points))
        painter.end()
    
class H_o_button_container(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(3)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setFixedSize(85, 38) 
        
        for _ in range(3):
            self.layout.addWidget(Select_hardware_output_buttons(slider_number=_+1))

class Hardware_output_text(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.device_a1_text = "Select Output Device"
        self.device_a2_text = ""
        self.device_a3_text = ""

        for i in range(3):
            name = f"H_Out_A{i+1}"
            Ctx[name] = ""
            Ctx.add_callback(name, self.update_device_text)

        self.setFixedSize(220, 70)

    def update_device_text(self):
        print("update_device_text")
        for i in range(3):
            name = f"H_Out_A{i+1}"
            if Ctx.get(name) is None:
                print("cannot find", name)
                continue

            if Ctx[name] == "" and i == 0:
                Ctx[name] = "Select Output Device"

            self.set_device_text(f"A{i+1}", Ctx[name])

    def set_device_text(self, output_key, new_text):
        target_key = f"device_{output_key.lower()}_text"
        if not hasattr(self, target_key):
            raise KeyError(f"Cannot find attribute '{target_key}'")

        setattr(self, target_key, new_text)

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w_rect = self.rect()
        padding_left = 6
        content_width = w_rect.width() - (padding_left * 2)

        font_title = QFont("Arial")
        font_title.setPixelSize(12)
        font_title.setBold(True)
        painter.setFont(font_title)
        painter.setPen(QPen(QColor("#8faac2")))

        y = 2 
        rect_title = QRect(padding_left, y, content_width, 14)
        painter.drawText(rect_title, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "HARDWARE OUT")
        y += 15

        font_device = QFont("Arial")
        font_device.setPixelSize(10)
        font_device.setWeight(QFont.Weight.Normal)
        painter.setFont(font_device)
        painter.setPen(QPen(QColor("#d1d1d6")))

        texts = [self.device_a1_text, self.device_a2_text, self.device_a3_text]
        for text in texts:
            if text:
                rect = QRect(padding_left, y, content_width, 13)
                painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            y += 14


class Select_h_i_container(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(6)
        # self.layout.setContentsMargins(10, 14, 5, 0)
        self.setFixedHeight(200)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.h_o_button_container = H_o_button_container(self)
        self.hardware_text = Hardware_output_text(Ctx["window"])
        self.hardware_text.move(720,30)

        self.layout.addWidget(self.h_o_button_container, alignment=Qt.AlignmentFlag.AlignTop)
        # self.layout.addWidget(self.hardware_text,  alignment=Qt.AlignmentFlag.AlignTop)

class VirtualInputsContainer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.vaio_text = "AudioMeeter VAIO"
        self.aux_text = "AudioMeeter AUX"
        
        self.setMinimumSize(200, 80)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        w_rect = self.rect()
        top_offset = 6
        
        line_pen = QPen(QColor("#2d3d4a"), 1)
        painter.setPen(line_pen)
        painter.drawLine(w_rect.left(), w_rect.top() + top_offset, w_rect.left(), w_rect.bottom() - 10)
        
        font_title = QFont("Arial")
        font_title.setPixelSize(12)
        font_title.setBold(True)
        painter.setFont(font_title)
        painter.setPen(QPen(QColor("#8faac2")))
        
        title_rect = QRect(w_rect.left(), w_rect.top() + top_offset, w_rect.width(), 16)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "VIRTUAL INPUTS")
        
        font_device = QFont("Arial")
        font_device.setPixelSize(10)
        font_device.setWeight(QFont.Weight.Normal)
        painter.setFont(font_device)
        painter.setPen(QPen(QColor("#a2a2a2")))
        
        half_width = w_rect.width() // 2
        
        vaio_rect = QRect(w_rect.left(), title_rect.bottom() + 2, half_width, 14)
        painter.drawText(vaio_rect, Qt.AlignmentFlag.AlignCenter, self.vaio_text)
        
        aux_rect = QRect(w_rect.left() + half_width, title_rect.bottom() + 2, half_width, 14)
        painter.drawText(aux_rect, Qt.AlignmentFlag.AlignCenter, self.aux_text)
        
        painter.end()

class MicsContainer(QWidget):
    def __init__(self, parent=None, slider_number=1):
        super().__init__(parent)
        self.slider_number = slider_number
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.setMinimumSize(140, 80)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        
        w_rect = self.rect()
        
        top_offset = 6 

        line_pen = QPen(QColor("#2d3d4a"), 1)
        painter.setPen(line_pen)
        painter.drawLine(w_rect.left(), w_rect.top() + top_offset, w_rect.left(), w_rect.bottom() - 10)
        
        padding_left = 10
        content_width = w_rect.width() - (padding_left * 2)
        
        top_font = QFont("Arial")
        top_font.setPixelSize(11)
        top_font.setBold(True)
        painter.setFont(top_font)
        painter.setPen(QPen(QColor("#8faac2")))
        
        top_text = f"HARDWARE INPUT  {self.slider_number}"
        
        top_rect = QRect(w_rect.left() + padding_left, w_rect.top() + top_offset, content_width, 16)
        painter.drawText(top_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, top_text)
        
        bottom_font = QFont("Arial")
        bottom_font.setPixelSize(10)
        painter.setFont(bottom_font)
        painter.setPen(QPen(QColor("#a2a2a2")))
        
        bottom_text = "Select Input Device"
        bottom_rect = QRect(w_rect.left() + padding_left, top_rect.bottom() + 2, content_width, 14)
        painter.drawText(bottom_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, bottom_text)
        
        painter.end()

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(0)
        
        self.layout.setContentsMargins(0, 28, 0, 0)

        for _ in range(3):
            self.layout.addWidget(MicsContainer(slider_number=_+1))
        
        self.virtual_inputs = VirtualInputsContainer(self)
        self.layout.addWidget(self.virtual_inputs)
        
        self.select_container = Select_h_i_container(self)
        self.layout.addWidget(self.select_container, stretch=1)

        self.setFixedHeight(80)
        self.setFixedWidth(950) 

    def paintEvent(self, event):
        painter = QPainter(self)
        bg_color = "#36495a"
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRect(self.rect())
        painter.end()