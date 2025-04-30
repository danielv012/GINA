#include <Arduino.h>
#include <ESP32Servo.h>
#include <EEPROM.h>
#include <WiFi.h>
#include "transducer.h"
#include "HX711.h"


// Access Point Information.
char ssid[] = "Diet Coke";
char password[] = "Diet Coke";
const uint ServerPort = 23; // Telnet, unencrypted text.
WiFiServer Server(ServerPort);
WiFiClient RemoteClient;
IPAddress Ip(192,168,1,1);
IPAddress NMask(255,255,255,0);

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
Servo* valves[NUM_VALVES] = { &valve_n2, &valve_release, &valve_fuel, &valve_ox };

enum LogType {WARNING, TEST, OKAY, ERROR};

#define FUEL_PTD_INDEX 1
#define OX_PTD_INDEX 2

unsigned long lastPressureSendTime = 0;
const unsigned long pressureSendInterval = 3000;
double pressure_count = 0;
double fuel_pressure_sum = 0.0;
double ox_pressure_sum = 0.0;


void init_servo();
void decode_valve_command(String);
void servo_set(int, int);
void log(const LogType, const String);
void check_for_connections();

void setup() {
  Serial.begin(115200); // For printing.
  // Using GPIO 5 for RXD, 18 for TXD.
  Serial2.begin(115200, SERIAL_8N1, 5, 18);
  
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);
  WiFi.softAPConfig(Ip, Ip, NMask);
  Serial.print("Connect to IP address: ");
  Serial.println(WiFi.softAPIP());
  Server.begin(); // Starts listening.

  analogReadResolution(ADC_RESOLUTION);

  tare_fuel_pressure = tarePressure(FUEL_PTD_INDEX);
  tare_ox_pressure = tarePressure(OX_PTD_INDEX);

  load_cell.begin(DT_PIN, SCK_PIN);
  // Tare load cell.
  load_cell.set_scale();
  load_cell.tare();
}

void loop() 
{
  check_for_connections();

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

  if (RemoteClient.connected())
  {
    // If there are messages.
    if (RemoteClient.available())
    {
      String message = RemoteClient.readStringUntil('\n');
      message.trim();

      // If message starts with 'V'.
      if (message.startsWith("V"))
      {
        decode_valve_command(message);
      }
    }

    if (currentTime - lastPressureSendTime >= pressureSendInterval)
    {
      lastPressureSendTime = currentTime;

      float avg_fuel_pressure = fuel_pressure_sum / (float)pressure_count;
      float avg_ox_pressure = ox_pressure_sum / (float)pressure_count;

      // Serial.println(String(fuel_pressure_sum));
      // Serial.println(String(ox_pressure_sum));
      // Serial.println(String(pressure_count));

      fuel_pressure_sum = 0.0;
      ox_pressure_sum = 0.0;
      pressure_count = 0.0;

      String fuel_pressureStr = "psi_fuel=" + String(avg_fuel_pressure, 2);
      String ox_pressureStr = "psi_ox=" + String(avg_ox_pressure, 2);
      String combined_pressureStr = fuel_pressureStr + "\n" + ox_pressureStr;
      RemoteClient.write(combined_pressureStr.c_str());

      String fuel_tlm_string = "TLM:" + fuel_pressureStr + "\n";
      String ox_tlm_string = "TLM:" + ox_pressureStr + "\n";

      Serial2.write(fuel_tlm_string.c_str());
      Serial2.write(ox_tlm_string.c_str());

      
      // Serial.println(combined_pressureStr);
    }
  }

  if (load_cell.is_ready())
  {
    long reading = load_cell.read();
    // TODO: Convert
    // Serial.print("Raw reading: ");
    // Serial.println(reading);
  } else {
    // Serial.println("HX711 not ready");
  }
  
}

/**
 * @brief Takes a serial message, checks formatting, and sends a servo command if correct.
 * 
 * @param message 
 */
void decode_valve_command(String message)
{
  int valve_index = message.substring(1, 2).toInt();
  if (valve_index < 1 || valve_index > NUM_VALVES) { log(ERROR, "Invalid valve number."); }
  else
  {
    int colon_pos = message.indexOf(':');
      // If format is incorrect, or no angle follows.
    if (colon_pos == -1 || colon_pos + 1 >= message.length()) { log(ERROR, "\"" + message + "\" Invalid format. Use V#:angle (e.g., V2:135)"); }
    else
    {
      int angle = message.substring(colon_pos + 1).toInt();
      servo_set(valve_index, angle);
    }
  }
}

void init_servo(int index)
{
  switch (index)
  {
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

void servo_set(int index, int angle)
{
  Servo* target_servo = valves[index - 1];
  // Attach pin.
  init_servo(index);
  target_servo->write(angle);
  // After a delay, attach so not draining power.
  log(OKAY, "Writing angle " + String(angle) + " to servo " + String(index) + ".");
  delay(500);
  target_servo->detach();
  log(OKAY, "Detached servo " + index);
  
}

void log(const LogType log_type, const String message)
{
  String text = "";
  
  switch (log_type)
  {
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

  if (RemoteClient.connected())
  {
    RemoteClient.write(text.c_str(), text.length());
    Serial2.write(text.c_str(), text.length());
  }
  else
  {
    Serial.println("Client not connected. Logging through serial:");
    Serial.println(text);
  }
}

void check_for_connections()
{
  if (Server.hasClient())
  {
    // If already connected, reject new connection. Otherwise accept.
    if (RemoteClient.connected())
    {
      log(WARNING, "Connection rejected.");
      Server.available().stop(); // End connection.
    }
    else
    {
      log(OKAY, "Connection accepted.");
      RemoteClient = Server.available();
    }
  }
}