#include "HUSKYLENS.h"
#include <SoftwareSerial.h>

SoftwareSerial huskySerial(10, 11); // RX, TX
HUSKYLENS huskylens;

const int relayPin = 7; // Relay control pin (D7)

void setup() {
  Serial.begin(9600);
  huskySerial.begin(9600);

  pinMode(relayPin, OUTPUT);  // Set relay pin as OUTPUT

  // Check if HuskyLens is connected
  if (!huskylens.begin(huskySerial)) {
    Serial.println("HuskyLens not connected!");
    while (1); // Stop if not connected
  }

  Serial.println("HuskyLens initialized successfully.");
}

void loop() {
  bool cleanDetected = false;

  // Request data from HuskyLens
  if (huskylens.request()) {
    while (huskylens.available()) {
      HUSKYLENSResult result = huskylens.read();

      // Check if the detected color ID matches the clean solar panel's color (ID 1)
      if (result.ID == 1) {
        cleanDetected = true;
        break;
      }
    }
  }

  // If dust is detected (i.e., panel not recognized as clean)
  if (!cleanDetected) {
    Serial.println("Fan ON - Panel is Dirty or Unrecognized");
    digitalWrite(relayPin, HIGH);  // Turn on the relay (fan ON)
  } else {
    Serial.println("Fan OFF - Clean Panel Detected");
    digitalWrite(relayPin, LOW);   // Turn off the relay (fan OFF)
  }

  delay(5000);  // Check every 5 seconds
}