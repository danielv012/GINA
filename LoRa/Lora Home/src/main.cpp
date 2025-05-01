/**
 * @file main.cpp
 * @author Daniel Vayman (daniel@vayman.co)
 * @brief Code for home LoRa board.
 * @version 0.1
 * @date 2025-04-29
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
void transmitCommand(String);

// SX1262 has the following connections:
// NSS pin:   10
// DIO1 pin:  2
// NRST pin:  3
// BUSY pin:  9

constexpr const char* PACKET_ID = "DIET_COKE=";
constexpr const int PACKET_ID_LENGTH = 10;


int packet_count = 0;
bool transmitting = false;
String current_command = "";

// Transmission interval.
unsigned long last_transmission_time = 0; // Last transmission time.
const unsigned long transmission_interval = 400; // Milliseconds. TODO: back to 200

// Reception.
unsigned long last_reception_time = 0; // Last reception time.
unsigned long last_heartbeat_message_time = 0; // Last heartbeat message.
const unsigned long heartbeat_interval = 1000; // Milliseconds.

// Creates a new LoRA instance using SX1262 (Handled by heltec_unofficial)
// SX1262 radio = new Module(8, 14, 12, 13);

void setup() {
  heltec_setup(); // Brings up serial at 115200 bps and powers on display.
  
  // Initialize SX1262 with default settings.
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
    while (true) { delay(10); } //TODO: Change to retry or wait for retry command?
  }
}


void loop() {
  heltec_loop(); // Must be called to scan the button, hanmdle sleep, etc.



  unsigned long now = millis();

  // RECEIVE SERIAL - If serial is available for reading (from Control Panel)
  if (transmitting)
  {
    if (now - last_transmission_time >= transmission_interval) // Only transmits every 200ms.
    {
      transmitCommand(current_command);
      last_transmission_time = now;
    }
  }
  else if (Serial.available()) // Not transmitting.
  {
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

  // RECEIVE - If data has been received through radio. Always receives up-to-date.
  String packet;
  // Receives one packet from buffer.
  int state = radio.receive(packet);

  if (state == RADIOLIB_ERR_NONE)
  {
    // If it's our packet.
    if (packet.startsWith(PACKET_ID))
    {
      last_reception_time = now;
      packet = packet.substring(PACKET_ID_LENGTH);
    
      // Finds index of first '\n' (should be last for one packet).
      int end_index = packet.indexOf('\n', 0);
      if (end_index != -1) // Continues to next packet if newline.
      {
        String message = packet.substring(0, end_index);

        // If ACK message.
        if (message.startsWith("ACK:"))
        {
          String acknowledgement = message.substring(4);
          int id_index = acknowledgement.indexOf('#');
          int local_count = (acknowledgement.substring(id_index + 1)).toInt();
          // If ACK count is equal to the one previously sent.
          if (local_count == packet_count)
          {
            transmitting = false;
            packet_count++;
            Serial.println(message);
          }
        }
        else if (message.startsWith("TLM:"))
        {
          Serial.println(message);
        }
        else
        {
          Serial.println(message);
        }
      }
    }
  }
  else
  {
    // some other error occurred
    // Serial.print(F("failed to receive, code "));
    // Serial.println(state);
  }
  

  int seconds_ago = now - last_reception_time;


  if (now - last_heartbeat_message_time >= heartbeat_interval)
  {
    Serial.println("Last reception time: " + String(seconds_ago / 1000));
    last_heartbeat_message_time = now;
  }
}

/**
 * @brief NOTE: Longer messages will take too long to send, which causes erroneous behavior.
 * 
 * @param command 
 */
void transmitCommand(String command)
{
  String message = String(PACKET_ID) + command + '#' + packet_count + '\n';

  int state = radio.transmit(message);
  if (state == RADIOLIB_ERR_NONE)
  {
    Serial.println("Successfully transmitted " + message);
  }
  else if (state == RADIOLIB_ERR_PACKET_TOO_LONG)
  {
    // the supplied packet was longer than 256 bytes
    Serial.println(F("Packet too long!"));
  }
  else
  {
    // some other error occurred
    Serial.print(F("failed, code "));
    Serial.println(state);
  }
}

