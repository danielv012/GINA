import sys
import socket
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QTextEdit
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
            self.serial_connection = serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE) # Open Serial Port
        except serial.SerialException:
            self.output.append(f"SERIAL EXCEPTION: Connection to serial port {SERIAL_PORT} failed.")
            return
        # Connection successful.
        self.output.append(f"Serial connection to {SERIAL_PORT} successful.")

    def sendMessage(self):
        if self.serial_connection.is_open:
            message = self.input.text() # + "\n"
            self.serial_connection.write(message.encode())
            self.input.clear()
            self.output.append(f"Wrote \"{message}\" to serial.")
        else:
            self.output.append("Not connected.")

    def readData(self):
        data = self.socket.readAll().data().decode()
        self.output.append("ESP32: " + data.strip())

    
    def closeEvent(self, event):
        """
        Ensures serial connection closes before program terminates.
        """
        try:
            if self.serial_connection.is_open:
                self.serial_connection.close()
        except AttributeError:
            pass
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ControlPanel()
    window.show()
    sys.exit(app.exec())