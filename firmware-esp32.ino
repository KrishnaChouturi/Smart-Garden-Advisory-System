#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Add Wifi Credentials
const char* ssid = "";
const char* password = "";

const char* telemetryUrl = "https://smart-garden-advisory-system.onrender.com/api/submit-reading";
const char* recommendationUrl = "https://smart-garden-advisory-system.onrender.com/compute-recommendation";

const int SOIL_PIN = 34;

#define uS_TO_S_FACTOR 1000000ULL
#define TIME_TO_SLEEP  3600ULL

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("ESP32 Smart Garden Waking Up");

  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");

  int retryCount = 0;
  while (WiFi.status() != WL_CONNECTED && retryCount < 30) {
    delay(500);
    Serial.print(".");
    retryCount++;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nWi-Fi connection timed out, going back to sleep.");
    goToDeepSleep();
    return;
  }

  Serial.println("\nConnected.");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  int currentMoisture = readSoilMoisture();
  sendLiveTelemetry(currentMoisture);
  checkSystemRecommendation();
  goToDeepSleep();
}

void loop() {
}

int readSoilMoisture() {
  int rawSum = 0;
  for (int i = 0; i < 5; i++) {
    rawSum += analogRead(SOIL_PIN);
    delay(50);
  }
  int rawAnalog = rawSum / 5;

  int moisturePercent = map(rawAnalog, 2665, 1049, 0, 100);
  moisturePercent = constrain(moisturePercent, 0, 100);

  Serial.print("Raw ADC Average: ");
  Serial.print(rawAnalog);
  Serial.print(" -> Calculated Moisture: ");
  Serial.print(moisturePercent);
  Serial.println("%");

  return moisturePercent;
}

void sendLiveTelemetry(int moistureValue) {
  HTTPClient http;
  http.begin(telemetryUrl);
  http.setTimeout(60000);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<100> doc;
  doc["moisture_level"] = moistureValue;

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  Serial.println("Sending telemetry...");
  int httpResponseCode = http.POST(jsonPayload);

  if (httpResponseCode > 0) {
    Serial.print("Telemetry upload status code: ");
    Serial.println(httpResponseCode);
  }
  http.end();
}

void checkSystemRecommendation() {
  HTTPClient http;
  http.begin(recommendationUrl);
  http.setTimeout(60000);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<100> doc;
  doc["target_threshold"] = 40;
  String jsonPayload;
  serializeJson(doc, jsonPayload);

  Serial.println("Fetching recommendation...");
  int httpResponseCode = http.POST(jsonPayload);

  if (httpResponseCode == 200) {
    String responseBody = http.getString();

    StaticJsonDocument<300> resDoc;
    DeserializationError error = deserializeJson(resDoc, responseBody);

    if (!error) {
      String recommendation = resDoc["recommendation"].as<String>();
      Serial.print("Current recommendation: ");
      Serial.println(recommendation);
    }
  } else {
    Serial.print("Failed to query recommendation engine. Code: ");
    Serial.println(httpResponseCode);
  }

  http.end();
}

void goToDeepSleep() {
  Serial.println("Entering deep sleep for 1 hour.");
  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * uS_TO_S_FACTOR);
  esp_deep_sleep_start();
}