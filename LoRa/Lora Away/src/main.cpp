#include <Arduino.h>
#include <heltec_unofficial.h>

// Function headers.
void sendCommand(String);
void transmitMessage(String);

constexpr const char* PACKET_ID = "DIET_COKE=";
constexpr const int PACKET_ID_LENGTH = 10;

// Reception
unsigned long last_reception_time = 0; // Last reception time.
const unsigned long ping_timer = 3000; // Ping timer (how long to wait before closing valves)

void setup() {
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
    while (true) { delay(10); } 
  }
}

void loop() {
  heltec_loop(); // Must be called to scan the button, hanmdle sleep, etc.

  unsigned long now = millis();

  
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
      if (end_index != -1) // Continues to next packet if newline exists.
      {

        String message = packet.substring(0, end_index);

        // If CMD message (requires ACK).
        if (message.startsWith("CMD:"))
        {
          int id_index = message.indexOf('#');
          Serial.println("Message: " + message);
          Serial.println("Message subs: " + message.substring(id_index));
          int packet_count = (message.substring(id_index + 1)).toInt();
          String command = message.substring(4, id_index);
          Serial.println("PACKET_COUNT: " + packet_count);
          
          sendCommand(command);

          String acknowledgement = "ACK:#" + String(packet_count) + '\n';
          // Transmit acknowledgement 3 times.
          transmitMessage(acknowledgement);
          delay(100);
          transmitMessage(acknowledgement);
          delay(100);
          transmitMessage(acknowledgement);
          delay(100);
        }
      }
    }
  }
  else
  {
    // some other error occurred
    Serial.print(F("failed to receive, code "));
    Serial.println(state);
  }
  

  // If nothing has been heard for 3+ seconds, close valves.
  if (now - last_reception_time >= ping_timer)
  {
    String command = "CLOSE_VALVES";
    sendCommand(command);
  }

  // Transmit TLM message
  while (Serial2.available())
  {
    String message = Serial2.readStringUntil('\n');
    transmitMessage(message);
  }

  // TODO: Probably better to stack messages and then transmit in one packet?
}

void sendCommand(String command)
{
  Serial2.println(command);
}

void transmitMessage(String message)
{
  String packet = PACKET_ID + message + '\n';
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
    Serial.print(F("failed, code "));
    Serial.println(state);
  }
}