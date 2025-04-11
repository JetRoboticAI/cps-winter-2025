#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <TFT_eSPI.h>
#include <rpcWiFi.h>
#include <WiFiClientSecure.h>

#include "config.h"

WiFiClientSecure wioClient;
PubSubClient client(wioClient);
TFT_eSPI tft;

struct BusInfo {
  bool is_valid;
  // String trip_id;
  String route_number;
  String stop_name;
  unsigned long next_arrival_time;
  String formatted_time;
};

BusInfo busData[3];
int currentDisplayIndex = 0;
unsigned long lastUpdateTime = 0;
bool newDataAvailable = false;

void setup_wifi() {
  delay(10);
  tft.begin();
  tft.setRotation(3);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);
  tft.setCursor(0, 0);
  tft.println("Preparing for WiFi connection");
  delay(2000);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  // WiFi.begin(WIFI_SSID);

  tft.println("Conecting to WiFi...");

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    tft.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    tft.println("\nWiFi connected");
    tft.print("IP: ");
    tft.println(WiFi.localIP());
    delay(2000);
  } else {
    tft.println("\nWiFi connection failed");
    while (1)
      delay(1000);
  }
}

void displayBusInfo() {
  tft.fillScreen(TFT_BLACK);
  
  // Header with route info
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);
  tft.setCursor(0, 5);
  tft.print("Bus ");
  tft.print(currentDisplayIndex + 1);
  tft.print(": Route: ");
  tft.setTextColor(TFT_CYAN);
  tft.println(busData[currentDisplayIndex].route_number);
  
  // Draw separator line
  tft.drawFastHLine(0, 30, tft.width(), TFT_DARKGREY);

  // Stop info section
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(1);
  tft.setCursor(0, 35);
  tft.println("Current Stop:");
  tft.setTextSize(2);
  tft.setTextColor(TFT_YELLOW);
  tft.println(busData[currentDisplayIndex].stop_name);
  
  // Draw separator line
  tft.drawFastHLine(0, 70, tft.width(), TFT_DARKGREY);

  // Time remaining section
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(1);
  tft.setCursor(0, 75);
  tft.println("Arriving in:");
  
  unsigned long currentTime = millis() / 1000;
  int secondsRemaining = busData[currentDisplayIndex].next_arrival_time - currentTime;
  int minutes = secondsRemaining / 60;
  int seconds = secondsRemaining % 60;

  tft.setTextSize(4);
  if (minutes > 0) {
    tft.setTextColor(TFT_GREEN);
    tft.print(minutes);
    tft.setTextSize(2);
    tft.print("m ");
    tft.setTextSize(4);
    tft.print(seconds);
    tft.setTextSize(2);
    tft.println("s");
  } else {
    tft.setTextColor(TFT_RED);
    tft.print(seconds);
    tft.setTextSize(2);
    tft.println("s");
  }

  // Status bar at bottom
  tft.fillRect(0, tft.height() - 20, tft.width(), 20, TFT_DARKGREY);
  tft.setTextSize(1);
  tft.setTextColor(busData[currentDisplayIndex].is_valid ? TFT_GREEN : TFT_RED);
  tft.setCursor(5, tft.height() - 15);
  tft.print(busData[currentDisplayIndex].is_valid ? "VALID" : "INVALID");
  
  tft.setTextColor(TFT_WHITE);
  tft.setCursor(tft.width()/2, tft.height() - 15);
  tft.print("Updated: ");
  tft.print(millis() / 1000);
}

void callback(char *topic, byte *payload, unsigned int length) {
  StaticJsonDocument<256> doc;
  deserializeJson(doc, payload, length);

  // Determine which bus this message is for by comparing with MQTT_TOPICS
  int busIndex = -1;
  for (int i = 0; i < 3; i++) {
    if (strcmp(topic, MQTT_TOPICS[i]) == 0) {
      busIndex = i;
      break;
    }
  }
  if (busIndex == -1) return; // Unknown topic

  busData[busIndex].is_valid = doc["is_valid"];
  // busData[busIndex].trip_id = doc["trip_id"].as<String>();
  busData[busIndex].route_number = doc["route_number"].as<String>();
  busData[busIndex].stop_name = doc["stop_name"].as<String>();
  busData[busIndex].next_arrival_time = doc["next_arrival_time"];

  newDataAvailable = true;
  lastUpdateTime = millis();
}

void reconnect() {
  while (!client.connected()) {
    tft.fillScreen(TFT_BLACK);
    tft.setCursor(0, 0);
    tft.setTextColor(TFT_YELLOW);
    tft.println("Connecting to");
    tft.println("HiveMQ Cloud...");
    
    int state = client.state();
    if (client.connect("WioTerminalClient", MQTT_USER, MQTT_PASSWORD)) {
      tft.println("Connected!");
      for (int i = 0; i < 3; i++) {
        client.subscribe(MQTT_TOPICS[i]);
      }
      delay(1000);
    } else {
      tft.print("Failed, rc=");
      tft.println(state);  // Print detailed error info
      tft.print("Error: ");
      switch(state) {
        case MQTT_CONNECTION_TIMEOUT: tft.println("Connection timeout"); break;
        case MQTT_CONNECTION_LOST: tft.println("Connection lost"); break;
        case MQTT_CONNECT_FAILED: tft.println("Connect failed"); break;
        case MQTT_DISCONNECTED: tft.println("Disconnected"); break;
        case MQTT_CONNECT_BAD_PROTOCOL: tft.println("Bad protocol"); break;
        case MQTT_CONNECT_BAD_CLIENT_ID: tft.println("Bad client ID"); break;
        case MQTT_CONNECT_UNAVAILABLE: tft.println("Unavailable"); break;
        case MQTT_CONNECT_BAD_CREDENTIALS: tft.println("Bad credentials"); break;
        case MQTT_CONNECT_UNAUTHORIZED: tft.println("Unauthorized"); break;
        default: tft.println("Unknown error"); break;
      }
      tft.println("Retry in 5s...");
      delay(5000);
    }
  }
}


#define BUTTON_LEFT WIO_5S_LEFT
#define BUTTON_RIGHT WIO_5S_RIGHT

void setup() {
  tft.begin();
  tft.setRotation(3);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE);
  tft.setTextSize(2);
  tft.setCursor(0, 0);
  tft.println("Initializing...");

  // Initialize buttons
  pinMode(BUTTON_LEFT, INPUT_PULLUP);
  pinMode(BUTTON_RIGHT, INPUT_PULLUP);

  // Sleep for 2 seconds to allow the display to initialize
  delay(2000);

  setup_wifi();
  wioClient.setCACert(root_ca);
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Handle button presses
  if (digitalRead(BUTTON_LEFT) == LOW) {  // Left button
    delay(200);  // Debounce
    currentDisplayIndex = (currentDisplayIndex + 2) % 3;  // Cycle backward
    displayBusInfo();
  } else if (digitalRead(BUTTON_RIGHT) == LOW) {  // Right button
    delay(200);  // Debounce
    currentDisplayIndex = (currentDisplayIndex + 1) % 3;  // Cycle forward
    displayBusInfo();
  }

  if (newDataAvailable) {
    displayBusInfo();
    newDataAvailable = false;
  }

  static unsigned long lastUpdate = 0;
  if (millis() - lastUpdate >= 1000) {
    lastUpdate = millis();
    if (client.connected() && !newDataAvailable) {
      displayBusInfo();
    }
  }
}
