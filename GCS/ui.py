import time
from enum import Enum

from PyQt6.QtCore import Qt

from PyQt6.QtWidgets import (
    QPushButton,
    QTextEdit,
    QLineEdit,
    QLabel,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
)
from pyqtgraph import PlotWidget


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)


class HeartbeatLabel(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("Last Heartbeat: None recieved")
        self.setStyleSheet(
            """
            QLineEdit {
                background-color: black;
                color: white;
                font-weight: bold;
                border: 1px solid #373838;
                text-align: center;
            }
            """
        )
        self.setReadOnly(True)

    def update_heartbeat(self, hbt: str) -> None:
        self.setText(f"Last Heartbeat: {hbt} ago")


class ValveState(Enum):
    CLOSED = "CLOSE"
    OPEN = "OPEN"
    NEUTRAL = "NEUTRAL"


class ValveSwitchButton(QPushButton):
    def __init__(self, parent=None, text: str = "", callback=None):
        super().__init__(parent)
        self.setText(text)
        self.setFixedSize(40, 40)
        self.setStyleSheet(
            """
            QPushButton {
                background-color: #633854;
                color: white;
                font-weight: bold;
                border-radius: 20px;
            }

            QPushButton:hover {
                background-color: #43313F;
            }
            """
        )
        self.clicked.connect(callback)


class ValveSwitch(QWidget):
    def __init__(self, name: str, callback=None):
        super().__init__()

        self.name = name
        self.state_ = ValveState.CLOSED
        self.callback_ = callback

        self.label_ = QLabel()
        self.label_.setText(f"{self.name} [{self.state_.value}]")
        self.label_.setStyleSheet(
            """
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            """
        )

        self.layout_ = QVBoxLayout()
        self.layout_.addWidget(self.label_, 0, Qt.AlignmentFlag.AlignCenter)

        self.inner_layout_ = QHBoxLayout()
        self.inner_layout_.setSpacing(70)
        # Center the buttons
        self.inner_layout_.addWidget(
            ValveSwitchButton(
                self,
                "O",
                callback=lambda: self.proxy_callback_(ValveState.OPEN),
            )
        )
        self.inner_layout_.addWidget(
            ValveSwitchButton(
                self, "C", callback=lambda: self.proxy_callback_(ValveState.CLOSED)
            )
        )
        self.inner_layout_.addWidget(
            ValveSwitchButton(
                self, "N", callback=lambda: self.proxy_callback_(ValveState.NEUTRAL)
            )
        )
        self.inner_layout_.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_.addLayout(self.inner_layout_)
        self.layout_.addWidget(QHLine())

        self.setLayout(self.layout_)

    def proxy_callback_(self, state: ValveState):
        """Proxy callback's only job is to set the text of the label before calling the real callback."""
        self.state_ = state
        self.label_.setText(f"{self.name} [{self.state_.value}]")
        self.callback_(state)


class ConnectButton(QPushButton):
    def __init__(self, parent=None, callback=None):
        super().__init__(parent)
        self.setText("Connect")
        self.setStyleSheet(
            """
            QPushButton {
                background-color: #26e029;  /* Green */
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }

            QPushButton:hover {
                background-color: #009900;  /* Darker green on hover */
            }
            """
        )
        self.clicked.connect(callback)


class IgnitionButton(QPushButton):
    def __init__(self, parent=None, callback=None):
        super().__init__(parent)
        self.setText("Ignite")
        self.setFixedSize(50, 50)
        self.setStyleSheet(
            """
            QPushButton {
                background-color: red;
                color: white;
                font-weight: bold;
                border-radius: 25px;
                border: 2px solid black;
            }
            QPushButton:hover {
                background-color: #cc0000;  /* Darker red on hover */
            }
            QPushButton:pressed {
                background-color: #990000;  /* Even darker red on click */
            }
            """
        )
        self.clicked.connect(callback)


class ImportantValveButton(QPushButton):
    def __init__(self, parent=None, text: str = "", callback=None):
        super().__init__(parent)
        self.setText(text)
        self.setFixedSize(50, 50)
        self.setStyleSheet(
            """
            QPushButton {
                background-color: #633854;
                color: white;
                font-weight: bold;
                border-radius: 25px;
            }

            QPushButton:hover {
                background-color: #43313F;
            }
            """
        )
        self.clicked.connect(callback)


class SerialOutputTerminal(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("Serial Output")
        self.setStyleSheet(
            """
            QTextEdit {
                background-color: black;
                color: white;
                font-weight: bold;
                border: 1px solid #373838;
                padding: 14px;
            }
            """
        )
        self.setReadOnly(True)


class PressureGraph(PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Fuel and Oxidizer Pressure")
        self.setLabel("left", "Pressure (psig)")
        self.setLabel("bottom", "Time (s)")
        self.setStyleSheet(
            """
            color: white;
            border: 1px solid #373838;
            """
        )
        self.legend = self.addLegend(offset=(1, -1), labelTextSize="7pt")
        self.fuel_curve = self.plot(name="Fuel PSI", pen="r")
        self.ox_curve = self.plot(name="OX PSI", pen="b")

        self.start_time = time.time()
        self.time = []
        self.psi_fuel_data = []
        self.psi_ox_data = []

    def reset(self) -> None:
        self.time = []
        self.psi_fuel_data = []
        self.psi_ox_data = []
        self.start_time = time.time()

    def update(self, psi_fuel: float, psi_ox: float) -> None:
        current_time = time.time() - self.start_time
        self.time.append(current_time)
        self.psi_fuel_data.append(psi_fuel)
        self.psi_ox_data.append(psi_ox)

        self.fuel_curve.setData(self.time, self.psi_fuel_data)
        self.ox_curve.setData(self.time, self.psi_ox_data)


class ThrustGraph(PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Thrust (N) vs Time (s)")
        self.setLabel("left", "Thrust (N)")
        self.setLabel("bottom", "Time (s)")
        self.setStyleSheet(
            """
            color: white;
            border: 1px solid #373838;
            """
        )

        self.start_time = time.time()
        self.time = []
        self.load_data = []

    def reset(self) -> None:
        self.time = []
        self.load_data = []
        self.start_time = time.time()

    def update(self, load_data: float) -> None:
        current_time = time.time() - self.start_time
        self.time.append(current_time)
        self.load_data.append(load_data)
        self.plot(self.time, self.load_data, name="Thrust (N)", pen="g")
