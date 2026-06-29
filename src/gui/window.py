import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout,QHBoxLayout, QSlider, QLabel, QPushButton
from .widgets import TitleBar,Mic_pannel, Virtual_input_panel, Hardware_panel
from .styler import Styler

import psutil
import os
import asyncio

from PySide6.QtCore import QTimer
from qasync import QEventLoop
from base import Ctx


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        Ctx["window"] = self

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

        self.panel_widget = QWidget(self.central_widget)
        self.panel_widget.setStyleSheet("background-color: transparent;")
        self.panel_widget.setFixedWidth(900)
        self.panel_widget.setFixedHeight(470)
        self.panel_widget.move(0, 75)

        self.panel_layout = QHBoxLayout(self.panel_widget) 
        self.panel_layout.setContentsMargins(0, 0, 0, 0) 
        self.panel_layout.setSpacing(0)

        print("ctx window: ")
        
        self.panel_layout.addWidget(Mic_pannel())
        self.panel_layout.addWidget(Virtual_input_panel())
        self.panel_layout.addWidget(Hardware_panel())
        

        self.layout.addStretch(1) 
        # ----------------------------

        # self.ram_timer = QTimer(self)
        # self.ram_timer.timeout.connect(self.log_ram_usage)
        # self.ram_timer.start(2000)

    def log_ram_usage(self):
        process = psutil.Process(os.getpid())
        ram_mb = process.memory_info().rss / (1024 * 1024)
        print(f"Anlık RAM Kullanımı: {ram_mb:.2f} MB")

