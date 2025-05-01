#include "HX711.h"
#include "transducer.h"
#include <Arduino.h>
#include <ArduinoJson.h>
#include <EEPROM.h>
#include <ESP32Servo.h>
#include <WiFi.h>
#include <cmath>

// Load cell pins.
#define DT_PIN 18
#define SCK_PIN 5

HX711 load_cell;

static const int NUM_VALVES = 4;

// Servo pins.
#define VALVE_N2_PIN 12
#define VALVE_RELEASE_PIN 27
#define VALVE_FUEL_PIN 25
#define VALVE_OX_PIN 32
Servo valve_n2;
Servo valve_release;
Servo valve_fuel;
Servo valve_ox;

const int open_valve_n2 = 95;
const int close_valve_n2 = 155;
const int open_valve_release = 82;
const int close_valve_release = 172;
const int open_valve_fuel = 85;
const int close_valve_fuel = 170;
const int open_valve_ox = 73;
const int close_valve_ox = 160;

// Array of servo pointers.
Servo *valves[NUM_VALVES] = {&valve_n2, &valve_release, &valve_fuel, &valve_ox};

enum LogType { WARNING, TEST, OKAY, ERROR };

#define FUEL_PTD_INDEX 1
#define OX_PTD_INDEX 2

unsigned long lastDataSendTime = 0;
const unsigned long dataSendInterval = 300;
double pressure_count = 0;
double fuel_pressure_sum = 0.0;
double ox_pressure_sum = 0.0;

void init_servo();
void decode_valve_command(String);
void servo_set(int, int);
void log(const LogType, const String);
void check_for_connections();
void command_function(String);

void setup() {
  Serial.begin(115200); // For printing.
  // Using GPIO 5 for RXD, 18 for TXD.
  Serial2.begin(115200, SERIAL_8N1, 5, 18);

  analogReadResolution(ADC_RESOLUTION);

  tare_fuel_pressure = tarePressure(FUEL_PTD_INDEX);
  tare_ox_pressure = tarePressure(OX_PTD_INDEX);

  load_cell.begin(DT_PIN, SCK_PIN);
  // Tare load cell.
  load_cell.set_scale(33.1656583);
  load_cell.set_offset(-163065.0);
  load_cell.tare();
}

void loop() {
  // TODO: check_for_connections();

  // // Read msg from serial.
  // if (Serial.available())
  // {
  //   String message = Serial.readStringUntil('\n');
  //   message.trim();
  //   // If message starts with 'V'.
  //   if (message.startsWith("V"))
  //   {
  //     decode_valve_command(message);
  //   }
  // }

  float fuel_pressure = readPressure(FUEL_PTD_INDEX) - tare_fuel_pressure;
  float ox_pressure = readPressure(OX_PTD_INDEX) - tare_ox_pressure;
  unsigned long currentTime = millis();
  pressure_count++;
  fuel_pressure_sum += fuel_pressure;
  ox_pressure_sum += ox_pressure;

  if (Serial2.available()) {
    // Read command from serial
    String message = Serial2.readStringUntil('\n');
    message.trim();

    // If message starts with 'V'.
    if (message.startsWith("V")) {
      decode_valve_command(message);
    }

    if (message.startsWith("CMD:")) {
      command_function(message);
    }
  }

  if (currentTime - lastDataSendTime >= dataSendInterval) {
    lastDataSendTime = currentTime;

    float avg_fuel_pressure = fuel_pressure_sum / (float)pressure_count;
    float avg_ox_pressure = ox_pressure_sum / (float)pressure_count;

    // Debugging, uncommented if needed.
    // Serial.println(String(fuel_pressure_sum));
    // Serial.println(String(ox_pressure_sum));
    // Serial.println(String(pressure_count));

    // Reset telemetry sums.
    fuel_pressure_sum = 0.0;
    ox_pressure_sum = 0.0;
    pressure_count = 0.0;

    JsonDocument msg;
    msg["psi_fuel"] = round(avg_fuel_pressure * 100.0) / 100.0;
    msg["psi_ox"] = round(avg_ox_pressure * 100.0) / 100.0;

    if (load_cell.is_ready()) {
      long reading = load_cell.get_units(10);
      msg["load"] = reading;
    }

    String serialized_msg;
    serializeJson(msg, serialized_msg);
    serialized_msg = "TLM:" + serialized_msg + "\n";
    Serial2.write(serialized_msg.c_str(), serialized_msg.length());
  }
}

/**
 * @brief Takes a serial message, checks formatting, and sends a servo command
 * if correct.
 *
 * @param message
 */
void decode_valve_command(String message) {
  int valve_index = message.substring(1, 2).toInt();
  if (valve_index < 1 || valve_index > NUM_VALVES) {
    log(ERROR, "Invalid valve number.");
  } else {
    int colon_pos = message.indexOf(':');
    // If format is incorrect, or no angle follows.
    if (colon_pos == -1 || colon_pos + 1 >= message.length()) {
      log(ERROR,
          "\"" + message + "\" Invalid format. Use V#:angle (e.g., V2:135)");
    } else {
      int angle = message.substring(colon_pos + 1).toInt();
      servo_set(valve_index, angle);
    }
  }
}

void init_servo(int index) {
  switch (index) {
  case 1:
    valve_n2.attach(VALVE_N2_PIN);
    break;
  case 2:
    valve_release.attach(VALVE_RELEASE_PIN);
    break;
  case 3:
    valve_fuel.attach(VALVE_FUEL_PIN);
    break;
  case 4:
    valve_ox.attach(VALVE_OX_PIN);
    break;
  default:
    log(WARNING, "Wrong servo index provided for pin attachment.");
    break;
  }
}

void servo_set(int index, int angle) {
  Servo *target_servo = valves[index - 1];
  // Attach pin.
  init_servo(index);
  target_servo->write(angle);
  // After a delay, attach so not draining power.
  log(OKAY,
      "Writing angle " + String(angle) + " to servo " + String(index) + ".");
  delay(500);
  target_servo->detach();
  log(OKAY, "Detached servo " + index);
}

void log(const LogType log_type, const String message) {
  String text = "";

  switch (log_type) {
  case WARNING:
    text += "WARNING: ";
    break;
  case TEST:
    text += "TEST: ";
    break;
  case OKAY:
    text += "OKAY: ";
    break;
  case ERROR:
    text += "ERROR: ";
    break;
  default:
    break;
  }
  text += message;

  if (RemoteClient.connected()) {
    RemoteClient.write(text.c_str(), text.length());
    Serial2.write(text.c_str(), text.length());
  } else {
    Serial.println("Client not connected. Logging through serial:");
    Serial.println(text);
  }
}

void command_function(String command) {
  // ignition_sequence();
}