import serial

from PyQt6.QtCore import pyqtSignal, QObject


class SerialMonitor(QObject):
    """
    Separate worker thread to constantly monitor serial data and signal GUI thread.
    """

    data_received = pyqtSignal(str)

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
