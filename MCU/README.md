ESP32 handles hardware control
Wifi socket connects my macbook to ESP32
Macbook runs a GUI to display telemeetry and send commands
Config files (YAML) are stored on macbook and can be updated via the GUI. Stores servo open/closed positions, tare data, whatever

Valve control serial command format:

"V<valve_number>:<angle>" where angle is 0-180 inclusive
Example: "V1:90" would set valve 1 to 90 degrees