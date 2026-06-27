import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QSlider, QLabel, QPushButton
from PySide6.QtCore import Qt
from .styler import Styler

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.Styler = Styler()

        self.setWindowTitle("Audiomeeter")
        self.setFixedSize(900, 545)
        self.setStyleSheet("background-color: rgb(255, 255, 255);")
        
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        self.layout = QVBoxLayout(self.central_widget)
        
        self.debug_slider = QSlider(Qt.Orientation.Vertical)
        self.Styler.set_style("slider", self.debug_slider)
        self.debug_slider.setMinimumWidth(120)

        self.layout.addWidget(self.debug_slider)


# DEBUG
app = QApplication(sys.argv)
w = Window()
w.show()
sys.exit(app.exec())