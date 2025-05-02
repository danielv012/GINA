#include "HX711.h"
#include "transducer.h"
#include <Arduino.h>
#include <ArduinoJson.h>
#include <EEPROM.h>
#include <ESP32Servo.h>
#include <WiFi.h>
#include <cmath>

// Function Headers
void init_servo();
void decode_valve_command(String);
void servo_set(int, int);
void log(const LogType, const String);
void check_for_connections();
void decodeCommand(String);
void close_all_valves();
void open_all_valves();
void ignition_sequence();
int get_servo_angle(int valve_index, String angle);
void ignition_start();
void ignition_stop();

// Load cell pins.
#define DT_PIN 18
#define SCK_PIN 5
// Load cell object.
HX711 load_cell;

// Igniter relay pin.
#define RELAY_PIN 22

/////////// VALVES ///////////////
// Servo pins.
#define VALVE_N2_PIN 12
#define VALVE_RELEASE_PIN 27
#define VALVE_FUEL_PIN 25
#define VALVE_OX_PIN 32
static const int NUM_VALVES = 4;
Servo valve_n2;
Servo valve_release;
Servo valve_fuel;
Servo valve_ox;

// NITROGEN VALVE
const int open_valve_n2 = 95;
const int close_valve_n2 = 150;
const int neutral_valve_n2 = 120;

// RELEASE VALVE
const int open_valve_release = 82;
const int close_valve_release = 172;
const int neutral_valve_release = 130;

// FUEL VALVE
const int open_valve_fuel = 85;
const int close_valve_fuel = 170;
const int neutral_valve_fuel = 130;

// OX VALVE
const int open_valve_ox = 73;
const int close_valve_ox = 150;
const int neutral_valve_ox = 110;

// Array of servo pointers.
Servo *valves[NUM_VALVES] = {&valve_n2, &valve_release, &valve_fuel, &valve_ox};
////////////////////////////////////

enum LogType
{
    WARNING,
    TEST,
    OKAY,
    ERROR
};

#define FUEL_PTD_INDEX 1
#define OX_PTD_INDEX 2
double pressure_count = 0;
double fuel_pressure_sum = 0.0;
double ox_pressure_sum = 0.0;

unsigned long lastDataSendTime = 0;
const unsigned long dataSendInterval = 300;

const unsigned long fire_length = 5000;
unsigned long ignition_time = 0;
bool firing = false;

void setup()
{
    Serial.begin(115200); // For debugging.
    // Using GPIO 5 for RXD, 18 for TXD.
    Serial2.begin(115200, SERIAL_8N1, 16, 17);

    analogReadResolution(ADC_RESOLUTION);

    // Tare pressure.
    tare_fuel_pressure = tarePressure(FUEL_PTD_INDEX);
    tare_ox_pressure = tarePressure(OX_PTD_INDEX);

    load_cell.begin(DT_PIN, SCK_PIN);
    // Tare load cell.
    load_cell.set_scale(33.1656583);
    load_cell.set_offset(-163065.0);
    load_cell.tare();

    pinMode(RELAY_PIN, OUTPUT);
}

void loop()
{
    unsigned long currentTime = millis();

    // If Serial2 (command) is available.
    if (Serial2.available())
    {
        // Read command.
        String message = Serial2.readStringUntil('\n');
        // Crops whitespace, newline, etc.
        message.trim();
        Serial.println("Received from Serial2: " + message);

        if (message.startsWith("CMD:"))
        {
            decodeCommand(message);
        }
    }

    // Read pressures.
    float fuel_pressure = readPressure(FUEL_PTD_INDEX) - tare_fuel_pressure;
    float ox_pressure = readPressure(OX_PTD_INDEX) - tare_ox_pressure;

    pressure_count++;
    fuel_pressure_sum += fuel_pressure;
    ox_pressure_sum += ox_pressure;

    // Sending telemetry every 300ms. Calculates averages.
    if (currentTime - lastDataSendTime >= dataSendInterval)
    {

        float avg_fuel_pressure = fuel_pressure_sum / (float)pressure_count;
        float avg_ox_pressure = ox_pressure_sum / (float)pressure_count;

        // Debugging, uncommented if needed.
        // Serial.println(String(fuel_pressure_sum));
        // Serial.println(String(ox_pressure_sum));
        // Serial.println(String(pressure_count));
        // Serial.print("Fuel tare: " + String(tare_fuel_pressure));
        // Serial.print("Ox tare: " + String(tare_ox_pressure));

        // Reset telemetry sums.
        fuel_pressure_sum = 0.0;
        ox_pressure_sum = 0.0;
        pressure_count = 0.0;

        JsonDocument msg;
        msg["psi_fuel"] = round(avg_fuel_pressure * 100.0) / 100.0;
        msg["psi_ox"] = round(avg_ox_pressure * 100.0) / 100.0;

        if (load_cell.is_ready())
        {
            long reading = load_cell.get_units(10);
            msg["load"] = reading;
        }

        // Write via Serial2 to LoRa away.
        String serialized_msg;
        serializeJson(msg, serialized_msg);
        serialized_msg = "TLM:" + serialized_msg + "\n";
        Serial2.print(serialized_msg);

        // DEBUG:
        Serial.print("Wrote Serial2: " + serialized_msg);

        lastDataSendTime = currentTime;
    }

    // IGNITION.
    if (firing)
    {
        currentTime = millis();
        // If we have been firing for 5+ seconds, stop.
        if (currentTime - ignition_time >= fire_length)
        {
            ignition_stop();
        }
    }
}

/**
 * @brief Takes a serial message, checks formatting, and sends a servo command
 * if correct.
 *
 * @param message
 */
void decode_valve_command(String message)
{
    int valve_index = message.substring(1, 2).toInt();
    // Serial.println("Decoding command:" + message);
    if (valve_index < 1 || valve_index > NUM_VALVES)
    {
        log(ERROR, "Invalid valve number. Message: " + message + ". Num: " + valve_index);
        return;
    }

    int colon_pos = message.indexOf(':');
    // If format is incorrect, or no command follows colon e.g. "V1:".
    if (colon_pos == -1 || colon_pos + 1 >= message.length())
    {
        log(ERROR, "\"" + message + "\" Invalid format. Use V#:angle (e.g., V2:OPEN)");
        return;
    }

    // Ex. V1:OPEN
    message.trim();
    String angle_string = message.substring(colon_pos + 1);
    int servo_angle = get_servo_angle(valve_index, angle_string);
    servo_set(valve_index, servo_angle);
}

void init_servo(int index)
{ // TODO: Maybe init all servos on start?
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
    Servo *target_servo = valves[index - 1];
    // Attach pin.
    init_servo(index);
    target_servo->write(angle);
    // After a delay, attach so not draining power.
    log(OKAY,
        "Writing angle " + String(angle) + " to servo " + String(index) + ".");
}

void decodeCommand(String command)
{
    // Crops "CMD:" header. Redundant check.
    if (command.startsWith("CMD:"))
        command = command.substring(4);

    if (command.startsWith("IGN"))
    {
        // Will not start ignition again on a duplicate packet.
        if (!firing)
            ignition_start();
    }
    else if (command.startsWith("OPEN_ALL"))
    {
        open_all_valves();
    }
    else if (command.startsWith("CLOSE_ALL"))
    {
        close_all_valves();
    }
    else if (command.startsWith("V"))
    {
        decode_valve_command(command);
    }
}

// SEQUENCES /////////////////////////////
void close_all_valves()
{
    decode_valve_command("V1:CLOSE");
    decode_valve_command("V2:CLOSE");
    decode_valve_command("V3:CLOSE");
    decode_valve_command("V4:CLOSE");
}

void open_all_valves()
{
    decode_valve_command("V1:OPEN");
    decode_valve_command("V2:OPEN");
    decode_valve_command("V3:OPEN");
    decode_valve_command("V4:OPEN");
}

// IGNITION.
void ignition_start()
{
    digitalWrite(RELAY_PIN, HIGH);
    delay(500);
    decode_valve_command("V3:OPEN");
    decode_valve_command("V4:OPEN");
    ignition_time = millis();
    firing = true;
}

void ignition_stop()
{
    decode_valve_command("V3:CLOSE");
    decode_valve_command("V4:CLOSE");
    digitalWrite(RELAY_PIN, LOW);
    firing = false;
}
/////////////////////////////////////////////

/**
 * @brief Returns the correct servo position for given command.
 *
 * @param valve_index
 * @param angle
 * @return int
 */
int get_servo_angle(int valve_index, String angle)
{
    switch (valve_index)
    {
    // Nitrogen
    case 1:
        if (angle.equals("OPEN"))
            return open_valve_n2;
        else if (angle.equals("CLOSE"))
            return close_valve_n2;
        else // NEUTRAL
            return neutral_valve_n2;
        break;
    // Release
    case 2:
        if (angle.equals("OPEN"))
            return open_valve_release;
        else if (angle.equals("CLOSE"))
            return close_valve_release;
        else // NEUTRAL
            return neutral_valve_release;
        break;
    // Fuel
    case 3:
        if (angle.equals("OPEN"))
            return open_valve_fuel;
        else if (angle.equals("CLOSE"))
            return close_valve_fuel;
        else // NEUTRAL
            return neutral_valve_fuel;
        break;
    // Oxygen
    case 4:
        if (angle.equals("OPEN"))
            return open_valve_ox;
        else if (angle.equals("CLOSE"))
            return close_valve_ox;
        else // NEUTRAL
            return neutral_valve_ox;
        break;
    default:
        log(ERROR, "Wrong servo index provided for getting servo angle.");
        return -999;
    }
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

    Serial.println(text);
    Serial2.println(text);
}