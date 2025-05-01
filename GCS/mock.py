import serial
import time
import json
import random

# Configure the serial port
ser = serial.Serial(port="/dev/pts/5", baudrate=9600, timeout=1)  # Adjust as needed

# Check if the port is open
if not ser.is_open:
    ser.open()

try:
    while True:
        # Send heartbeat message
        hbt = random.randint(0, 5)
        ser.write(f"HBT:{str(hbt)}\n".encode("utf-8"))
        # Generate two random values for psi_fuel and psi_ox
        psi_fuel = random.randint(0, 1000)
        psi_ox = random.randint(0, 1000)
        msg = {
            "psi_fuel": psi_fuel,
            "psi_ox": psi_ox,
        }

        should_include_load = random.randint(0, 1) == 1
        if should_include_load:
            msg["load"] = random.randint(0, 100000)

        message = "TLM:" + json.dumps(msg) + "\n"
        ser.write(message.encode("utf-8"))
        print(f"Sent: {message.strip()}")
        time.sleep(0.5)  # 500ms delay
except KeyboardInterrupt:
    print("Interrupted by user.")
finally:
    ser.close()
    print("Serial port closed.")
