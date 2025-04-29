/**
 * 5V 1000 PSI Pressure transducer (PT) reader.
 * PT info:
 https://www.ebay.com/itm/225037793734?_skw=pressure+transducer+1%2F8+NPT+500+PSI&itmmeta=01JP1RSB7GDZE8FEZKYYV1XXFM&hash=item34654c39c6:g:KUMAAOSwMT1isB7k&itmprp=enc%3AAQAKAAABAFkggFvd1GGDu0w3yXCmi1eJ4sylJhl5arzINv6VBdBlYf4zwBckDkmKmF8Fsv6d9gKp6xezc9rwBv2Mr4aXMCnnHytw%2FgYlr8cHtHF5rjXY3hyqCzB2Qj94UgY%2B36g9lrz%2FJoAmnXKYW7VR16LoNFVlv9iEfzayJ35x71AKBRvOHN5nGB%2Fb4xGKs4M59FZzZqHW9wP788wrlmY5Uryk0yiQ9J8aH0dJEEriufsdC%2BXoMiCicgir5K3y%2BjS%2BaVErlM2zmfFr73pGMQ2tk7A7WjB1ZirrUdvefbyvguF3lA2rrshGYLxafXnucZSxBGX1E5n3xNwllzgKrm0JbzkGkCg%3D%7Ctkp%3ABFBM-rPluLBl

  * Input: 0-1000 psi.
  * Output: 0.5V – 4.5V linear voltage output. 0 psi outputs 0.5V, 500 psi
  * outputs 2.5V, 1000 psi outputs 4.5V.
  * Works for oil, fuel, water or air pressure. Can be used in oil tank, gas,
    tank, etc.
  * Accuracy: within 2% of reading (full scale).
  * Thread: 1/8” NPT.
  * Wiring connector: water sealed quick disconnect. Mating connector is
    included.
  * Wiring: Red for +5V. Black for ground. Blue for signal output.
  * Weight: 70 g
 */


 #include <Arduino.h>
 #include "transducer.h"

//  // CHANGEME: An ADC pin, baud rate, and ADC voltage/resolution.
//  #define SENSOR_PIN 36
//  #define BAUD_RATE 115200
//  #define ADC_MAX_VOLTAGE 3.3
//  #define ADC_RESOLUTION 12
 
//  // The number of samples to take when taring the sensor.
//  const int TARE_SAMPLES = 100;
//  // The delay between samples when taring the sensor.
//  const int TARE_DELAY_MS = 10;
 
//  // The max ADC value. See:
//  // https://www.arduino.cc/reference/tr/language/functions/analog-io/analogread/
//  const float ADC_MAX_VALUE = (1 << ADC_RESOLUTION) - 1; // 2^RESOLUTION - 1
 
//  // Sensor info.
//  const float SENSOR_MIN_VOLTAGE = 0.5;
//  const float SENSOR_MAX_VOLTAGE = 4.5;
//  const float MAX_PSI = 1000;
 
 // The tared pressure at atmospheric pressure, for calibration.
 float tare_fuel_pressure = 0;
 float tare_ox_pressure = 0;

 /**
  * Reads the pressure from the sensor.
  * @param ptd_index 1:fuel, 2: oxygen
  * @return The pressure in PSI.
  */
 float readPressure(int ptd_index) {

   int adc_value = 0;

   if (ptd_index == 1) // Read from fuel ptd.
   {
    adc_value = analogRead(FUEL_PTD_PIN);
   }
   else // Assuming oxygen.
   {
    adc_value = analogRead(OX_PTD_PIN);
   }
   

  //  Serial.println(String(adc_value));
 
   // ADC value is an integer between 0 and 2^RESOLUTION - 1.
   // To convert it to a voltage, we scale it back to ADC voltage.
   // See:
   // https://www.arduino.cc/reference/tr/language/functions/analog-io/analogread/
   float voltage = (adc_value / ADC_MAX_VALUE) * ADC_MAX_VOLTAGE;
   // Apply inverse voltage divider ratio to scale back to 0.5-4.5.
   float r_1 = 1.0; // kOhm
   float r_2 = 2.0; // kOhm
   float voltage_divider_ratio = r_2/(r_1 + r_2);
   voltage /= voltage_divider_ratio;
 
   // To convert the voltage to PSI, scale to the sensor's min and max
   // voltage.
   float psi = ((voltage - SENSOR_MIN_VOLTAGE) /
                (SENSOR_MAX_VOLTAGE - SENSOR_MIN_VOLTAGE)) *
               MAX_PSI;
 
   return psi;
 }
 
 /**
  * Tares the sensor by taking multiple samples and averaging them.
  * @return The tared pressure.
  */
 float tarePressure(int ptd_index) {
   float sum = 0;
   for (int i = 0; i < TARE_SAMPLES; i++) {
     sum += readPressure(ptd_index);
     delay(TARE_DELAY_MS);
   }
 
   return sum / TARE_SAMPLES;
 }