import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QSlider, QLabel, QPushButton
from .widgets import Mic_slider, Slider_buttons_div, TitleBar, Mic_container, Mic_pannel
from .styler import Styler

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.styler = Styler()
        self.setWindowTitle("Audiomeeter")
        self.setFixedSize(900, 545)
        self.setStyleSheet("background-color: #2f4050;")
        
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.layout.addWidget(TitleBar())
        self.layout.addWidget(Mic_pannel())
        
        # self.layout.addWidget(Mic_slider())

        # self.layout.addWidget(Slider_buttons_div())
        # self.layout.addWidget(Hardware_slider())

        # self.layout.addWidget(Circle_slider())





# DEBUG
app = QApplication(sys.argv)
w = Window()
w.show()
sys.exit(app.exec())