#include <Servo.h> // Importing library to operate the servo easily

const int trigPin = 9;   // Setting pin 9 of arduino for trigger pin of ultrasonic sensor
const int echoPin = 10;  // Setting pin 10 of arduino for echo pin of ultrasonic sensor
const int motorPin = 5;  // Setting pin 5 (PWM capable pin) of arduino for operating vibration motor 
const int servoPin = 6;  // Setting pin 6 of arduino for operating servo motor 

Servo myservo; 
int pos = 90;    // variable to store the servo position
int distanceThreshold = 20;  // Initializing threshold distance to be 20 cm

void setup() {
  // Setting input and output pins
  pinMode(trigPin, OUTPUT); // Setting ultrasonic trigger pin as output
  pinMode(echoPin, INPUT); // Setting ultrasonic echo pin as input
  pinMode(motorPin, OUTPUT); // Setting motor control pin as output
  myservo.attach(servoPin); // Attaching servo control as pin 6
  Serial.begin(9600); // Starting serial communication at 9600 bits/ s for serial communication with laptop/ system
  
  Serial.println("System Ready - Move object closer to test motor");
}
// Function to calculate obstacle distance using ultrasonic sensor
int getUltrasonicDistance() {
  // Emmitting a short burst of ultrasonic soundwave from the trigger pin
  digitalWrite(trigPin, LOW);
  delayMicroseconds(10);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Emmitting a short burst of ultrasonic soundwave from the trigger pin
  long duration = pulseIn(echoPin, HIGH); // Measures the time (in microseconds) till the echo pin receives the signal.
  int distance = duration * 0.0343 / 2; // Calculating obstacle distance in cm (speed of sound= 343 m/s)

  if (duration == 0) {
    Serial.println("No Echo Received!");
    return -1;  // Error code
  }
  
  return distance;
}

void detectObject()
{
  int distance = getUltrasonicDistance();  // Calling the function to detect obstacle
// Printing obstacle distance
  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.println(" cm");
// Varying the motor vibration respective to the proximity of the obstacle (Higher intensity with closer proximity)
  if (distance > 0 && distance <= distanceThreshold) {  
    if (distance =< 15 && distance > 10){
    analogWrite(motorPin, 85); 
    Serial.println("Object Detected");} 
    if (distance =< 10 && distance > 5){
    analogWrite(motorPin, 170); 
    Serial.println("Object in proximity");}
        if (distance =< 5 && distance >= 0){
    analogWrite(motorPin, 255); 
    Serial.println("Object in close proximity");}}
  else {
    digitalWrite(motorPin, LOW);  
    Serial.println("Motor OFF - No Object Nearby");
  }

  delay(500);  
}

void loop() {
  // Loop to oscillate the servo
  for (pos = 45; pos <= 135; pos += 15) { // Goes from 45 degrees to 135 degrees hence at a step of 15 degrees, covering a total angle of 90 degrees (Clockwise motion)
    myservo.write(pos);              // Instruct the servo to go to position in variable 'pos'
    delay(15);    
    detectObject();                  
  }
  for (pos = 135; pos >= 45; pos -= 15) { // Similar to the above motion but in counterclockwise direction
    myservo.write(pos);              // Instruct the servo to go to position in variable 'pos'
    delay(15);                       // waits 15ms for the servo to reach the position
    detectObject();
  }
}