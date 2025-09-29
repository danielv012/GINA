/**
 * @file main.cpp
 * @author Daniel Vayman (daniel@vayman.co)
 * @brief Firmware for Lora Away (Radio receiver board conneced to ESP32 MCU)
 * @version 1.0
 * @date 2025-05-20
 *
 * @copyright Copyright (c) 2025
 *
 */

#include <Arduino.h>
#include <heltec_unofficial.h>

// Function headers.
void sendCommand(String);
void transmit(String);
void processPacket(String packet);

// Radio packet header.
constexpr const char *PACKET_ID = "DC=";
constexpr const int PACKET_ID_LENGTH = 3;

// Reception.
unsigned long last_reception_time = 0; // Last reception time.
const unsigned long ping_timer = 8000; // Ping timer (how long to wait before closing valves)

bool idle = false;

// Radio interrupt flag.
static volatile bool received_flag;
bool transmitting = false;

/**
 * @brief Stupid function that's needed. radio.available() should work.
 *
 */
void set_flag(void)
{
    if (transmitting)
    {
        transmitting = false;
        return;
    }
    received_flag = true;
}

void setup()
{
    heltec_setup(); // Brings up serial at 115200 bps and powers on display.

    // Wired Serial setup. RX: 19. TX: 20.
    Serial2.begin(115200, SERIAL_8N1, 19, 20);

    // Initialize Radio (SX1262) with default settings.
    Serial.print(F("[SX1262] Initializing ... "));
    int state = radio.begin();
    if (state == RADIOLIB_ERR_NONE)
    {
        radio.setFrequency(915.0);

        Serial.println(F("Success!"));
        // Set LED pin as output
        pinMode(LED_PIN, OUTPUT);
        digitalWrite(LED_PIN, HIGH);
    }
    else
    {
        Serial.print(F("Failed, code "));
        Serial.println(state);
        while (true)
        {
            delay(10);
        }
    }

    // Initializing callback.
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
        Serial.println("Radio is available.");
        String data;
        int state = radio.readData(data);
        Serial.println("Data: " + data);
        if (state == RADIOLIB_ERR_NONE)
            processPacket(data);
        else
        {
            Serial.print(F("Failed to read data from radio buffer, code "));
            Serial.println(state);
        }
    }

    // Checks for telemetry.
    if (Serial2.available())
    {
        String message = Serial2.readStringUntil('\n');

        // If it's telemetry, transmit.
        if (message.startsWith("T"))
        {
            Serial.println("Telemetry received: " + message);
            transmit(message);
        }
    }

    now = millis();
    // If nothing has been heard for 3+ seconds, close valves.
    if (now - last_reception_time >= ping_timer)
    {
        String command = "CMD:CLOSE_VALVES";
        if (!idle)
        {
            sendCommand(command);
            idle = true;
        }
    }
}

/**
 * @brief Called after receiving a packet.
 *
 * @param packet
 */
void processPacket(String packet)
{
    // If it's not our packet, return.
    if (!packet.startsWith(PACKET_ID))
        return;

    last_reception_time = millis();
    String message = packet.substring(PACKET_ID_LENGTH);

    // Finds index of first '\n' (expected last for one packet).
    int newline_index = message.indexOf('\n', 0);
    if (newline_index == -1) // Continues to next packet if newline exists.
    {
        Serial.println("Packet did not contain newline.");
        return;
    }

    // Crops newline character.
    message = message.substring(0, newline_index);

    // If CMD message (requires ACK).
    if (message.startsWith("CMD:"))
    {
        int id_index = message.indexOf('#');
        int packet_count = (message.substring(id_index + 1)).toInt();
        // Crops header and #. CMD:V1:OPEN_ALL#5 -> V1:OPEN_ALL
        String command = message.substring(0, id_index);
        sendCommand(command);
        idle = false;

        String acknowledgement = "ACK:#" + String(packet_count) + '\n';

        // Transmit acknowledgement 3 times.
        transmit(acknowledgement);
        delay(200);
        transmit(acknowledgement);
        delay(200);
        transmit(acknowledgement);
        delay(200);
    }
}

/**
 * @brief Writes commands to MCU.
 *
 * @param command
 */
void sendCommand(String command)
{
    // Writes and adds a newline. NOTE: Serial2 is wired TX/RX.
    Serial2.println(command);
    Serial.println("Wrote " + command + " to serial2.");
}

/**
 * @brief Transmits radio message.
 *
 * @param message
 */
void transmit(String message)
{
    String packet = PACKET_ID + message + '\n';

    transmitting = true;

    int state = radio.transmit(packet);
    if (state == RADIOLIB_ERR_NONE)
    {
        Serial.println("Successfully transmitted " + packet);
    }
    else if (state == RADIOLIB_ERR_PACKET_TOO_LONG)
    {
        // the supplied packet was longer than 256 bytes
        Serial.println(F("Packet too long!"));
    }
    else
    {
        // some other error occurred
        Serial.print(F("Failed transmission, code "));
        Serial.println(state);
    }

    // Begin receiving again. NOTE: DO NOT REMOVE.
    radio.startReceive();
}