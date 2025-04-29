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

// SX1262 has the following connections:
// NSS pin:   10
// DIO1 pin:  2
// NRST pin:  3
// BUSY pin:  9

// Creates a new LoRA instance using SX1262 (Handled by heltec_unofficial)
// SX1262 radio = new Module(8, 14, 12, 13);

void setup() {
  heltec_setup(); // Brings up serial at 115200 bps and powers on display.

  // Set LED pin as output
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);

  // Initialize SX1262 with default settings.
  Serial.print(F("[SX1262] Initializing ... "));
  int state = radio.begin();
  if (state == RADIOLIB_ERR_NONE)
  {
    Serial.println(F("Success!"));
  }
  else
  {
    Serial.print(F("Failed, code "));
    Serial.println(state);
    while (true) { delay(10); } //TODO: Change to retry or wait for retry command?
  }
}

// Counter to keep track of transmitted packets.
int count = 0;

void loop() {
  heltec_loop(); // Must be called to scan the button, hanmdle sleep, etc.

  // display.clear();
  // display.setFont(ArialMT_Plain_24);
  // display.drawString(0, 0, "Hey Daniel!");
  // display.display();

  // TODO:
  // 1. Read a string from serial. ex: CMD:OPEN_VALVES
  // If a proper command, save the command string
  // Start transmitting command string every 200ms. DIET_COKE:

  // 2. Transmit command

  // 3. Receive via radio
  // If ACK, increase counter
  // If TLM (telemetry), write to serial
  
  // 4. Write to serial.
  

  

  // NOTE: Commands will look like this:
  /**
   * OPEN_VALVES#<packet_number>
   * Will trasnmit 5 times, so the recevier could receive
   * OPEN_VALVES#123
   * OPEN_VALVES#123
   * OPEN_VALVES#123
   * OPEN_VALVES#123
   * OPEN_VALVES#123
   * But it'll keep track of the packet number, so if it already
   * received a packet then itll ignore.
   * You can transmit C-string or Ardunio string
   * up to 256 characters long.
  */

  
  String str = "Hello World! #" + String(count++);
  Serial.println("On...");
  Serial.print(F("[SX1262] Trasnmitting packet ... "));
  int state = radio.transmit(str);

  if (state == RADIOLIB_ERR_NONE)
  {
    // If the packet was successfully trasnmitted.
    Serial.println(F("Success!"));

    // Print measured data rate.
    Serial.print(F("[SX1262] Datarate:\t"));
    Serial.print(radio.getDataRate());
    Serial.println(F(" bps"));

  }
  else if (state == RADIOLIB_ERR_PACKET_TOO_LONG)
  {
    // the supplied packet was longer than 256 bytes
    Serial.println(F("too long!"));
  }
  else
  {
    // some other error occurred
    Serial.print(F("failed, code "));
    Serial.println(state);
  }
  
  // Delay before next packet.
  delay(100);
}

