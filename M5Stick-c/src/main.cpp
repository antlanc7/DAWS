#include <Arduino.h>
#include <driver/i2s.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/semphr.h>

#define SAMPLING_FREQUENCY_HZ     2000
#define BUFFER_LENGTH             64

#define CMD_START                 0x01
#define CMD_STOP                  "stop"

#define WIFI_SSID                 "Galaxy S8"//"Quercia"//"RaspM5"//"TIM-19801747"
#define WIFI_PSWD                 "ciaociao"//"queratolo"//"Gruppo6Ciao"//"R4QTQv5Yb3maOsan0ZxCBJd5"

#define SERVER_ADDRESS            "192.168.43.117"//"192.168.3.1"//"192.168.43.72"
#define SERVER_PORT               3125

#define ADC                       36

#define EVENT_ACQ_END_BIT         ( 1 << 0 )

TaskHandle_t dataForwarderTskHandle;
WiFiClient cmd_client;

EventGroupHandle_t eg;

void getDataT( void * uint8tTime );


void setup() {

  eg = xEventGroupCreate();
  Serial.begin( 9600 );
  pinMode( ADC, INPUT );

  Serial.println("Setting up WiFi connection.");
  WiFi.begin( WIFI_SSID, WIFI_PSWD );
  Serial.println("\tConnecting to WiFi:");
  Serial.print("\t\tSSID: ");
  Serial.println(WIFI_SSID);
  Serial.print("\t");
  while (! WiFi.isConnected()) {
    Serial.print(".");
    delay(500);
  }
  Serial.println("\n\tWiFi connected!");

  Serial.println("Setting up TCP/IP connection.");
  if ( cmd_client.connect(SERVER_ADDRESS, SERVER_PORT) ) {
    Serial.println("\tConnected to the server");
    Serial.print("\tSERVER IP: ");
    Serial.println(SERVER_ADDRESS);
    Serial.print("\tSERVER PORT: ");
    Serial.println(SERVER_PORT);
  } else {
    Serial.println("\tIMPOSSIBLE to connect with server.");
    while ( 1 );
  }
}


void loop() {
  if ( cmd_client.available() ) {
    uint8_t cmd[ 2 ];
    cmd_client.readBytes( cmd, sizeof(cmd) );
    if ( ( cmd[0] == CMD_START ) && ( cmd[1] != 0 ) ) {
      TickType_t xLastWakeTime;
      TickType_t xLastWakeTimeTemp;
      Serial.println("Starting acquisition task.");

      xTaskCreatePinnedToCore( & getDataT, "GET DATA", 4096, & cmd[1], 5, NULL, 1 );

      EventBits_t xbit = xEventGroupWaitBits( eg, EVENT_ACQ_END_BIT, pdTRUE, pdTRUE, portMAX_DELAY );
      /*
      xLastWakeTime = xTaskGetTickCount();
      xLastWakeTimeTemp = xLastWakeTime;
      vTaskDelayUntil( &xLastWakeTime, ( cmd[1] * 1000 ) / portTICK_PERIOD_MS );
      Serial.printf("Acquisition task stopped. Elapsed time: %d ms\n", ( xTaskGetTickCount() - xLastWakeTimeTemp ) / portTICK_PERIOD_MS );
      */
     Serial.println("Acquisition ended.");
    }
  }
  vTaskDelay( 1 / portTICK_PERIOD_MS );
}


void getDataT( void * uint8tTime) {
  TickType_t tTime = ( * ( ( uint8_t * ) uint8tTime) ) * 1000 * portTICK_PERIOD_MS;
  uint16_t samples[ BUFFER_LENGTH ];

  if ( SAMPLING_FREQUENCY_HZ == 0) {
    Serial.println("\t\tDIVISION BY ZERO. ACQUISITION_FREQ_HZ MUST BE > 0");
    vTaskDelete(NULL);
  }

  uint16_t usDelay = 1000000 / SAMPLING_FREQUENCY_HZ;

  TickType_t xLastWakeTime;
  unsigned long now = 0;

  xLastWakeTime = xTaskGetTickCount();
  
  while ( xTaskGetTickCount() - xLastWakeTime  <= tTime ) {
    for ( int i = 0; i < BUFFER_LENGTH; i += 1 ) {
      while ( micros() - now <= usDelay );
      now = micros();
      
      samples[i] = analogRead( ADC );
    }
    cmd_client.write( ( uint8_t * ) samples, sizeof( samples ) );
  }
  cmd_client.write( CMD_STOP );
  vTaskDelay( 50 / portTICK_PERIOD_MS );
  xEventGroupSetBits( eg, EVENT_ACQ_END_BIT );
  vTaskDelete( NULL );
}