import sys
import socket
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
)
from PyQt6.QtNetwork import QTcpSocket, QAbstractSocket
from PyQt6.QtCore import QIODevice, QThread, pyqtSignal, QObject

# NOTE: No longer using wifi.
# host = "192.168.1.1"
# port = 23

SERIAL_PORT = "/dev/tty.usbserial-0001"
SERIAL_BAUDRATE = 115200


class ControlPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        self.serial_connection = serial.Serial()

    def initUI(self):
        self.resize(1200, 800)
        self.setWindowTitle("GINA Control Panel")
        self.input = QLineEdit(self)
        self.input.setPlaceholderText("Enter command (e.g. V2:30)")

        self.sendBtn = QPushButton("Send", self)
        self.sendBtn.clicked.connect(self.sendMessage)

        self.connectBtn = QPushButton("Connect", self)
        self.connectBtn.clicked.connect(self.connectToHome)

        self.output = QTextEdit(self)
        self.output.setReadOnly(True)

        layout = QVBoxLayout()
        layout.addWidget(self.input)
        layout.addWidget(self.sendBtn)
        layout.addWidget(self.connectBtn)
        layout.addWidget(self.output)

        self.setLayout(layout)

    def connectToHome(self):
        try:
            self.serial_connection = serial.Serial(
                SERIAL_PORT, SERIAL_BAUDRATE
            )  # Open Serial Port
        except serial.SerialException:
            self.output.append(
                f"SERIAL EXCEPTION: Connection to serial port {SERIAL_PORT} failed."
            )
            return
        # Connection successful.
        self.output.append(f"Serial connection to {SERIAL_PORT} successful.")

        # Starts monitor thread.
        self.serial_monitor_thread = QThread()
        self.serial_monitor = SerialMonitor(self.serial_connection)
        self.serial_monitor.moveToThread(self.serial_monitor_thread)

        # Connects a slot (callback function) to the monitor data-received signal.
        self.serial_monitor.data_received.connect(self.displaySerialData)
        # Connects start signal to running function.
        self.serial_monitor_thread.started.connect(self.serial_monitor.run)
        self.serial_monitor_thread.start()

    def sendMessage(self):
        """
        Write a string over serial to Lora Home (UTF-8 encoded)
        """
        if self.serial_connection.is_open:
            message = "CMD:" + self.input.text() + "\n"
            self.serial_connection.write(message.encode())
            self.input.clear()
            self.output.append(f'Wrote "{repr(message)}" to serial.')
        else:
            self.output.append("Not connected.")

    def displaySerialData(self, data: str):
        self.output.append("LoRa Home: " + data)

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


class SerialMonitor(QObject):
    """
    Separate worker thread to constantly monitor serial data and signal GUI thread.
    """

    data_received = pyqtSignal(str)
    # finished = pyqtSignal()

    def __init__(self, serial_connection: serial.Serial):
        super().__init__()
        self.serial_connection = serial_connection
        self._running = True

    def run(self):
        while self._running:
            # Returns number of bytes in buffer.
            if self.serial_connection.in_waiting:
                try:
                    line = (
                        self.serial_connection.readline()
                        .decode(errors="ignore")
                        .strip()
                    )
                    # Sends signal with data.
                    self.data_received.emit(line)
                except Exception as e:
                    self.data_received.emit(f"ERROR: Read error {e}")

    def stop(self):
        self._running = False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ControlPanel()
    window.show()
    sys.exit(app.exec())
