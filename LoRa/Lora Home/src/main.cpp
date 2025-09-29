/**
 * @file main.cpp
 * @author Daniel Vayman (daniel@vayman.co)
 * @brief Code for home LoRa board (connected to Macbook Pro)
 * @version 1.0
 * @date 2025-05-20
 *
 * @copyright Copyright (c) 2025
 *
 */

#include <Arduino.h>
// #include <RadioLib.h>
#include <heltec_unofficial.h>
// https://registry.platformio.org/libraries/jgromes/RadioLib/examples/SX126x/SX126x_Transmit_Blocking/SX126x_Transmit_Blocking.ino
// https://registry.platformio.org/libraries/ropg/Heltec_ESP32_LoRa_v3
// https://registry.platformio.org/libraries/thingpulse/ESP8266%20and%20ESP32%20OLED%20driver%20for%20SSD1306%20displays/installation
// https://github.com/Heltec-Aaron-Lee/WiFi_Kit_series
// https://github.com/HelTecAutomation/Heltec_ESP32

// Function Headers
void processPacket(String packet);
String formatCommand(String command);
void transmit(String packet);

// Header for radio packets.
constexpr const char *PACKET_ID = "DC=";
constexpr const int PACKET_ID_LENGTH = 3;

int packet_count = 0;
bool transmitting = false;
String current_command = "";

// Transmission interval.
unsigned long last_transmission_time = 0;        // Last transmission time.
const unsigned long transmission_interval = 500; // Milliseconds.

// Ping interval (automatic valve closure).
const unsigned long ping_interval = 4000; // Milliseconds.

// Reception.
unsigned long last_reception_time = 0;         // Last reception time.
unsigned long last_heartbeat_message_time = 0; // Last heartbeat message.
const unsigned long heartbeat_interval = 5000; // Milliseconds.

// Radio interrupt flag.
static volatile bool received_flag;
bool transmitting_flag = false;

/**
 * @brief Stupid function that we need. radio.available() should work. I love broken libraries.
 *
 */
void set_flag(void)
{
    if (transmitting_flag)
    {
        transmitting_flag = false;
        return;
    }
    received_flag = true;
}

void setup()
{
    heltec_setup(); // Brings up serial at 115200 bps and powers on display.

    // Initialize SX1262 with default settings.
    Serial.print(F("[SX1262] Initializing ... "));
    int state = radio.begin();
    if (state == RADIOLIB_ERR_NONE)
    {
        radio.setFrequency(915.0);

        Serial.println(F("Success!"));
        // Set LED pin as output to signal radio health.
        pinMode(LED_PIN, OUTPUT);
        digitalWrite(LED_PIN, HIGH);
    }
    else
    {
        Serial.print(F("Failed, code "));
        Serial.println(state);
        while (true)
        {
            delay(10); // Holds Lora board in idle.
        }
    }

    // Sets callback.
    radio.setPacketReceivedAction(set_flag);

    // Non-blocking. Will automatically fill packet if received. Overwrites
    // buffer each packet.
    radio.startReceive();
}

void loop()
{
    heltec_loop(); // Must be called to scan the button, hanmdle sleep, etc.

    unsigned long now = millis();

    // If there's a packet in the buffer.
    if (received_flag)
    {
        received_flag = false;
        String data;
        int state = radio.readData(data);
        if (state == RADIOLIB_ERR_NONE)
            processPacket(data);
        else
        {
            Serial.print(F("Failed to read data from radio buffer, code "));
            Serial.println(state);
        }
    }

    // If serial was written by control panel UI.
    if (Serial.available())
    {
        // Get serial command. NOTE: Must end with '\n'.
        String message = Serial.readStringUntil('\n');
        // If command message, transmit.
        if (message.startsWith("CMD:"))
        {
            current_command = message;
            transmitting = true;
        }
        else
        {
            Serial.println("WARNING: Will only transmit commands with \"CMD:\" prefix.");
        }
    }

    now = millis(); // Accurate time.
    if (transmitting)
    {
        // Only transmits *commands* every X milliseconds.
        if (now - last_transmission_time >= transmission_interval)
        {
            String packet = formatCommand(current_command);
            transmit(packet);
            last_transmission_time = now;
        }
    }
    else
    {
        // Only transmits *pings* ever second.
        if (now - last_transmission_time >= ping_interval)
        {
            String packet = String(PACKET_ID) + "PING\n";
            transmit(packet);
            last_transmission_time = now;
        }
    }

    // Last heard from.
    now = millis();
    int seconds_ago = now - last_reception_time;
    if (now - last_heartbeat_message_time >= heartbeat_interval)
    {
        // Heart beat.
        Serial.println("HBT: " + String(seconds_ago / 1000));
        last_heartbeat_message_time = now;
    }
}

/**
 * @brief Called after receiving a packet.
 *
 * @param packet
 */
void processPacket(String packet)
{
    // If it's our packet.
    if (!packet.startsWith(PACKET_ID))
        return;

    last_reception_time = millis();
    // Crops header.
    String message = packet.substring(PACKET_ID_LENGTH);

    // Finds index of first '\n' (expected last index).
    int newline_index = message.indexOf('\n', 0);
    if (newline_index == -1) // Continues to next packet if newline.
    {
        Serial.println("Packet did not contain newline.");
        return;
    }

    // Crops newline character.
    message = message.substring(0, newline_index);

    // If ACK message.
    if (message.startsWith("ACK:"))
    {
        // Crops ACK: header.
        String acknowledgement = message.substring(4);
        int id_index = acknowledgement.indexOf('#');
        int local_count = (acknowledgement.substring(id_index + 1)).toInt();
        // If ACK count is equal to the one previously sent.
        if (local_count == packet_count)
        {
            transmitting = false;
            packet_count++;
            Serial.print("Received acknowledgement: ");
            Serial.println(message);
        }
    }
    else if (message.startsWith("T"))
    {
        Serial.println(message);
    }
    else // Just prints all messages to control panel for now.
    {
        Serial.println(message);
    }
}

/**
 * @brief Returns a formatted packet for commands.
 *
 * @param command
 * @return String
 */
String formatCommand(String command)
{
    return String(PACKET_ID) + command + '#' + packet_count + '\n';
}

/**
 * @brief NOTE: Longer messages may take too long to send, which causes
 * erroneous behavior.
 *
 * @param command
 */
void transmit(String packet)
{
    transmitting_flag = true;

    // Blocking, so control loop will wait for entire packet.
    int state = radio.transmit(packet);
    if (state == RADIOLIB_ERR_NONE)
    {
        Serial.println("ransmitted " + packet);
    }
    else if (state == RADIOLIB_ERR_PACKET_TOO_LONG)
    {
        // The supplied packet was longer than 256 bytes.
        Serial.println(F("Packet too long!"));
    }
    else
    {
        // Some other error occurred.
        Serial.print(F("Failed transmission, code "));
        Serial.println(state);
    }

    // Begin receiving again. NOTE: DO NOT REMOVE.
    radio.startReceive();
}