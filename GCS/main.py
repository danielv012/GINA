import sys
import json
import serial
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QFrame,
    QGraphicsDropShadowEffect,
    QSplitter,
    QHBoxLayout,
)
from PyQt6.QtGui import QColor, QPalette, QFont
from PyQt6.QtCore import QThread, Qt

from ui import (
    IgnitionButton,
    ImportantValveButton,
    ConnectButton,
    SerialOutputTerminal,
    PressureGraph,
    ThrustGraph,
    ValveSwitch,
)
from serial_monitor import SerialMonitor
from utils import g_to_N

COLOR_PALETTE = QPalette()
COLOR_PALETTE.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))

COMMANDS = {
    "IGN": "CMD:IGN\n",
    "FUEL_PRESSURIZATION:OPEN": "CMD:V1:OPEN\n",
    "FUEL_PRESSURIZATION:CLOSE": "CMD:V1:CLOSE\n",
    "FUEL_PRESSURIZATION:NEUTRAL": "CMD:V1:NEUTRAL\n",
    "FUEL_DEPRESSURIZATION:OPEN": "CMD:V2:OPEN\n",
    "FUEL_DEPRESSURIZATION:CLOSE": "CMD:V2:CLOSE\n",
    "FUEL_DEPRESSURIZATION:NEUTRAL": "CMD:V2:NEUTRAL\n",
    "FUEL_RELEASE:OPEN": "CMD:V3:OPEN\n",
    "FUEL_RELEASE:CLOSE": "CMD:V3:CLOSE\n",
    "FUEL_RELEASE:NEUTRAL": "CMD:V3:NEUTRAL\n",
    "OX_RELEASE:OPEN": "CMD:V4:OPEN\n",
    "OX_RELEASE:CLOSE": "CMD:V4:CLOSE\n",
    "OX_RELEASE:NEUTRAL": "CMD:V4:NEUTRAL\n",
    "CLOSE_ALL": "CMD:CLOSE_ALL\n",
    "OPEN_ALL": "CMD:OPEN_ALL\n",
}


def create_shadow_effect() -> QGraphicsDropShadowEffect:
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(15)
    shadow.setOffset(5, 5)  # Offset: bottom right
    shadow.setColor(QColor(0, 0, 0, 160))  # Semi-transparent black
    return shadow


class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.serial_connection = serial.Serial()
        self.serial_monitor_thread = None
        self.serial_port_path = "/dev/pts/6"
        self.serial_baudrate = "115200"

        self.initUI()

    def initUI(self):
        self.setWindowTitle("GINA Control Panel")
        self.serial_buadrate_input = QLineEdit(self)
        self.serial_buadrate_input.setPlaceholderText("Enter baudrate (e.g. 115200)")
        self.serial_buadrate_input.setText(self.serial_baudrate)
        self.serial_buadrate_input.textChanged.connect(
            lambda text: self.setSerialBaudrate(text)
        )

        self.serial_port_path_input = QLineEdit(self)
        self.serial_port_path_input.setPlaceholderText(
            "Enter serial port (e.g. /dev/tty.usbserial-0001)"
        )
        self.serial_port_path_input.setText(self.serial_port_path)
        self.serial_port_path_input.textChanged.connect(
            lambda text: self.setSerialPortPath(text)
        )

        self.command_input = QLineEdit(self)
        self.command_input.setPlaceholderText("Enter command (e.g. V2:30)")

        self.send_command_button = QPushButton("Send", self)
        self.send_command_button.clicked.connect(self.sendUserCommand)

        left_btn_panel = QFrame()
        left_btn_panel.setAutoFillBackground(True)
        left_btn_panel.setPalette(COLOR_PALETTE)
        left_btn_panel.setMaximumWidth(round(self.window().width() * 0.6))

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.serial_port_path_input)
        left_layout.addWidget(self.serial_buadrate_input)
        left_layout.addWidget(ConnectButton(self, self.connectToHome))
        left_layout.addWidget(
            ValveSwitch(
                "Fuel Pressurization Valve",
                callback=lambda state: (
                    self.serial_terminal.append(
                        f"Fuel Pressurization Valve : {state.value}"
                    ),
                    self.transmitMessage(
                        COMMANDS["FUEL_PRESSURIZATION:" + state.value]
                    ),
                ),
            )
        )
        left_layout.addWidget(
            ValveSwitch(
                "Fuel De-pressurization Valve",
                callback=lambda state: (
                    self.serial_terminal.append(
                        f"Fuel De-pressurization Valve : {state.value}"
                    ),
                    self.transmitMessage(
                        COMMANDS["FUEL_DEPRESSURIZATION:" + state.value]
                    ),
                ),
            )
        )

        important_btns_layout = QHBoxLayout()
        important_btns_layout.addWidget(
            IgnitionButton(self, callback=lambda: self.transmitMessage(COMMANDS["IGN"]))
        )
        important_btns_layout.addWidget(
            ImportantValveButton(
                self,
                "Close All",
                callback=lambda: self.transmitMessage(COMMANDS["CLOSE_ALL"]),
            )
        )
        important_btns_layout.addWidget(
            ImportantValveButton(
                self,
                "Open All",
                callback=lambda: self.transmitMessage(COMMANDS["OPEN_ALL"]),
            )
        )

        left_layout.addLayout(important_btns_layout)

        left_layout.addWidget(
            ValveSwitch(
                "OX Release Valve",
                callback=lambda state: (
                    self.serial_terminal.append(f"OX Release Valve : {state.value}"),
                    self.transmitMessage(COMMANDS["OX_RELEASE:" + state.value]),
                ),
            )
        )
        left_layout.addWidget(
            ValveSwitch(
                "Fuel Release Valve",
                callback=lambda state: (
                    self.serial_terminal.append(f"Fuel Release Valve : {state.value}"),
                    self.transmitMessage(COMMANDS["FUEL_RELEASE:" + state.value]),
                ),
            )
        )

        left_btn_panel.setLayout(left_layout)

        self.serial_terminal = SerialOutputTerminal(self)

        main_layout = QVBoxLayout()

        self.pressure_graph = PressureGraph(self)
        self.thrust_graph = ThrustGraph(self)

        right_panel = QFrame()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        right_panel.setAutoFillBackground(True)
        right_panel.setPalette(COLOR_PALETTE)
        right_layout.addWidget(self.command_input)
        right_layout.addWidget(self.send_command_button)
        right_layout.addWidget(self.serial_terminal)
        right_layout.addWidget(self.pressure_graph)
        right_layout.addWidget(self.thrust_graph)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_btn_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([10, 90])  # Left panel takes 20%, right panel takes 80%

        main_layout.addWidget(splitter)

        self.setLayout(main_layout)

    def setSerialPortPath(self, path: str):
        """
        Set the serial path for the connection.
        :param path: Serial port path.
        """
        self.serial_port_path = path

    def setSerialBaudrate(self, baudrate: str):
        """
        Set the baudrate for the connection.
        :param baudrate: Baudrate for serial communication.
        """
        self.serial_baudrate = baudrate

    def connectToHome(self):
        # Close any existing connection.
        if self.serial_monitor_thread:
            self.serial_monitor.stop()
            self.serial_monitor_thread.quit()
            self.serial_monitor_thread.wait()
        self.serial_connection.close()

        try:
            self.serial_connection = serial.Serial(
                self.serial_port_path, int(self.serial_baudrate)
            )  # Open Serial Port
        except serial.SerialException:
            self.serial_terminal.append(
                f"SERIAL EXCEPTION: Connection to serial port {self.serial_port_path} failed."
            )
            return
        except ValueError:
            self.serial_terminal.append(
                f"VALUE EXCEPTION: Invalid baudrate {self.serial_baudrate}."
            )
            return

        # Connection successful.
        self.serial_terminal.append(
            f"Serial connection to {self.serial_port_path} successful."
        )

        # Starts monitor thread.
        self.serial_monitor_thread = QThread()
        self.serial_monitor = SerialMonitor(self.serial_connection)
        self.serial_monitor.moveToThread(self.serial_monitor_thread)

        # Connects a slot (callback function) to the monitor data-received signal.
        self.serial_monitor.data_received.connect(self.displaySerialData)
        # Connects start signal to running function.
        self.serial_monitor_thread.started.connect(self.serial_monitor.run)
        self.serial_monitor_thread.start()

    def sendUserCommand(self):
        """
        Write a string over serial to Lora Home (UTF-8 encoded)
        """
        user_input = self.command_input.text()
        if not user_input:
            return

        message = "CMD:" + user_input + "\n"
        self.command_input.clear()
        self.transmitMessage(message)

    def transmitMessage(self, message: str):
        """
        Transmit a message over serial.
        :param message: Message to transmit.
        """
        if self.serial_connection.is_open:
            self.serial_connection.write(message.encode())
            self.serial_terminal.append(f'Wrote "{repr(message)}" to serial.')
        else:
            self.serial_terminal.append("Not connected.")

    def displaySerialData(self, data: str):
        if data.startswith("TLM:"):
            msg = json.loads(data[4:])
            self.pressure_graph.update(msg["psi_fuel"], msg["psi_ox"])
            if "load" in msg:
                self.thrust_graph.update(g_to_N(msg["load"]))
            self.serial_terminal.append("LoRa Home: " + data)
        else:
            self.serial_terminal.append("Debug: " + data)

    def closeEvent(self, event):
        """
        Ensures serial connection closes before program terminates.
        """
        self.serial_monitor.stop()
        self.serial_monitor_thread.quit()
        self.serial_monitor_thread.wait()  # Waits for the thread to finish executing.
        try:
            if self.serial_connection.is_open:
                self.serial_connection.close()
        except AttributeError:
            pass
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Roboto", 8)
    app.setFont(font)
    window = ControlPanel()
    window.setAutoFillBackground(True)
    window.setPalette(COLOR_PALETTE)
    window.show()
    sys.exit(app.exec())
