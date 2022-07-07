#include "ESP8266WiFi.h"
#include "WiFiClient.h"
#include <Servo.h>
#define SERVO_OPEN 180
#define SERVO_CLOSED 90
#define INPUT_PULSE_PIN 4
#define SERVO_PIN 5 // Wemos D1 (Pin D1)
#define MOVE_TIME 15000 // 15 seconds opening time

Servo myservo;  // create servo object to control a servo
// twelve servo objects can be created on most boards

int pos = SERVO_OPEN;    // variable to store the servo position
int loops = 0;

void setup() {
  // Setup the D2 PIN to INPUT (default HIGH). When the external relay closes the circuit, this will read GND.
  pinMode(INPUT_PULSE_PIN, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);
  
  Serial.begin(9600);
  Serial.println("Turning WiFi Off");
  WiFi.mode(WIFI_OFF);
  WiFi.forceSleepBegin();

  Serial.println("Enabling phaselock waveform");
  enablePhaseLockedWaveform();

  Serial.println("Attaching servo");
  myservo.attach(SERVO_PIN,544,2400);  // attaches the servo on pin 9 to the servo object

  Serial.println("Setting servo to OPEN status");
  delay(1000);
  myservo.write(SERVO_OPEN);
  delay(1000);

  Serial.println("Ready to go!");
}

bool waitPulse(int high_millisecs, int sampling_millisecs) {
  assert(high_millisecs>sampling_millisecs);
  
  // Read a pulse that lasts at least 1 second
  int count=0;
  int target_count=high_millisecs/sampling_millisecs;
  
  int pulse=digitalRead(INPUT_PULSE_PIN);
  while(pulse==LOW and count<target_count) {
    Serial.print("+");
    Serial.println(count);
    count+=1;
    pulse=digitalRead(INPUT_PULSE_PIN);
    delay(sampling_millisecs);
  }

  return count>=target_count;
}

void togglePos(int movetime) {
  assert(movetime>0);
  int targetPos;

  int dinterval = movetime/(SERVO_OPEN-SERVO_CLOSED);
  if (pos == SERVO_OPEN) {
    for (pos; pos>SERVO_CLOSED;pos--) {
      myservo.write(pos);
      delay(dinterval);
    }
  } else {
    for (pos; pos<SERVO_OPEN;pos++) {
      myservo.write(pos);
      delay(dinterval);
    }
  }  
}

void loop() {
  if (loops==0) {
    Serial.println("Waiting for input pulse...");
  }
  bool pulseDetected = waitPulse(1500, 100);

  if (pulseDetected) {
    Serial.println("Pulse Detected!");
    togglePos(MOVE_TIME);
    delay(3000); 
  }
  
  delay(100);
  loops+=1;
  if (loops==100)
    loops=0;
}
