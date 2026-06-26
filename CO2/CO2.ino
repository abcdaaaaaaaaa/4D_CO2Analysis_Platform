// ESP32 Wrover Module
// Partition Scheme: "Huge APP (3MB No OTA/1MB SPIFFS)"

#include "MG811.h"
#include <DHT.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <NetworkClientSecure.h>
#include <Deneyap_GPSveGLONASSkonumBelirleyici.h>

#define ADC_BIT_RESU (12)
#define gasPin       (34)
#define dhtPin       (33)

const char* ssid = "REPLACE_WITH_YOUR_SSID";  
const char* password = "REPLACE_WITH_YOUR_PASSWORD";
const char* serverName = "https://co2.uzay.info/datareceiver.php";

static const char* myWriteAPIKey = "PWIFQRC3WHDW6YG5";

GPS GPS;

float startTime = 0;

bool measuring = false;
bool windowLock = false;

float sensorVal, CO2, CH4, C2H5OH, CO, TheoreticalCO2, temp, rh, Time, Correction;
int Gas;

MG811 sensor(ADC_BIT_RESU, gasPin);
DHT dht(dhtPin, DHT22);

long round2(float x);
long round4(float x);
void sendData();
void postData(String httpRequestData);

void setup() {
  Serial.begin(115200);
  sensor.begin();
  dht.begin();

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  if (!GPS.begin(0x2F)) {
    delay(3000);
    Serial.println("I2C connection failed."); 
  }
}

void loop() {
  temp = dht.readTemperature();
  rh = dht.readHumidity();
  sensorVal = sensor.read();

  if(sensorVal == 0) {
    measuring = false;
    startTime = 0;
    windowLock = false;
    return;
  }

  if(!measuring && sensorVal > 0) {
    startTime = millis() / 1000.0;
    measuring = true;
    windowLock = false;
  }

  if(measuring) {
    float t = sensor.correction_time((millis() / 1000.0) - startTime);

    if(t >= 9 && t <= 11) {
      if(!windowLock) {
        sendData();
        windowLock = true;
      }
    } else {
      windowLock = false;
    }
  }
}

void sendData() {
  Time = sensor.correction_time((millis() / 1000.0) - startTime);
  Correction = sensor.calculateCorrection(Time);
  TheoreticalCO2 = sensor.TheoreticalCO2(sensorVal);

  CH4 = sensor.calculateppm(sensorVal, temp, rh, Correction, 0);
  C2H5OH = sensor.calculateppm(sensorVal, temp, rh, Correction, 1);
  CO = sensor.calculateppm(sensorVal, temp, rh, Correction, 2);
  CO2 = sensor.calculateppm(sensorVal, temp, rh, Correction, 3);

  Gas = analogRead(gasPin);

  GPS.readGPS(RMC);
  long lat = (long)((GPS.readLocationLat() + 90.0) * 10000000);
  long lng = (long)((GPS.readLocationLng() + 180.0) * 10000000);

  String request = "api_key=" + String(myWriteAPIKey) + 
                   "&field1=" + String(round2(Time)) + 
                   "&field2=" + String(round4(Correction)) + 
                   "&field3=" + String(round2(TheoreticalCO2)) + 
                   "&field4=" + String(round2(CO2)) + 
                   "&field5=" + String(round2(CH4)) + 
                   "&field6=" + String(round2(C2H5OH)) + 
                   "&field7=" + String(round2(CO)) + 
                   "&field8=" + String(Gas) +
                   "&field9=" + String((long)((temp + 140) * 10)) + 
                   "&field10=" + String((long)((rh + 100) * 10)) + 
                   "&field11=" + String(lat) + 
                   "&field12=" + String(lng);
  postData(request);
}

void postData(String httpRequestData) {
  NetworkClientSecure *client = new NetworkClientSecure;
  if(client) {
      client->setInsecure();
      HTTPClient http;
      if (http.begin(*client, serverName)) {
          http.addHeader("Content-Type", "application/x-www-form-urlencoded");
          int httpResponseCode = http.POST(httpRequestData);
          http.end();
      }
      delete client;
  }
}

long round2(float x) {
  return round(x * 100);
}

long round4(float x) {
  return round(x * 10000);
}
