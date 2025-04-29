#pragma once



float readPressure(int ptd_index);
float tarePressure(int ptd_index);

extern float tare_fuel_pressure;
extern float tare_ox_pressure;

 // CHANGEME: An ADC pin, baud rate, and ADC voltage/resolution.
 #define FUEL_PTD_PIN 39
 #define OX_PTD_PIN 34
 #define BAUD_RATE 115200
 #define ADC_MAX_VOLTAGE 3.3
 #define ADC_RESOLUTION 12
 
 // The number of samples to take when taring the sensor.
 const int TARE_SAMPLES = 100;
 // The delay between samples when taring the sensor.
 const int TARE_DELAY_MS = 10;
 
 // The max ADC value. See:
 // https://www.arduino.cc/reference/tr/language/functions/analog-io/analogread/
 const float ADC_MAX_VALUE = (1 << ADC_RESOLUTION) - 1; // 2^RESOLUTION - 1
 
 // Sensor info.
 const float SENSOR_MIN_VOLTAGE = 0.5;
 const float SENSOR_MAX_VOLTAGE = 4.5;
 const float MAX_PSI = 1000;