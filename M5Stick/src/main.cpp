#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/semphr.h>
#include <freertos/queue.h>
#include <M5StickC.h>
#include "wifi_creds.h"

#define SAMPLING_FREQUENCY_HZ     2000
#define BUFFER_LENGTH             64

#define CMD_START                 0x01
#define CMD_PING                  0x02
#define CMD_WHEREISIT             0x03
#define CMD_STOP                  "stop"

#define LED_PIN                   10
#define ADC_PIN                   36

#define EVENT_ACQ_END_BIT         ( 1 << 0 )

TaskHandle_t dataForwarderTskHandle;
WiFiClient cmd_client;

EventGroupHandle_t eg;
QueueHandle_t data;

int16_t cy;
uint8_t cmd[8];

void getDataT( void * uint8tTime );
void sendData( void * parameter );
void whereIsIt( void * parameter);


void setup() {
  M5.begin(); //inizializza anche la seriale a 115200 baud
  M5.Axp.EnableCoulombcounter();
  M5.Lcd.fillScreen( BLACK );
  M5.Lcd.setRotation( 3 );

  pinMode( ADC_PIN, INPUT );
  pinMode( LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  M5.Lcd.drawCircle( M5.Lcd.width() - 15, 7, 5, RED);

  M5.Lcd.setCursor( 5, 5 );
  M5.Lcd.println("Setting up WiFi.");
  WiFi.begin( WIFI_SSID, WIFI_PSWD );
  M5.Lcd.println(" Connecting to WiFi:");
  M5.Lcd.print("  SSID: ");
  M5.Lcd.println( WIFI_SSID );
  M5.Lcd.print("  ");
  while (! WiFi.isConnected()) {
    M5.Lcd.print(".");
    delay(500);
  }
  M5.Lcd.fillScreen( BLACK );
  M5.Lcd.fillCircle( M5.Lcd.width() - 15, 7, 5, GREEN );

  M5.Lcd.setCursor( 5, 5 );
  M5.Lcd.println( "TCP/IP connection:" );
  if ( cmd_client.connect(SERVER_ADDRESS, SERVER_PORT) ) {
    M5.Lcd.println( "Connected to the server" );
    M5.Lcd.print( "SERVER IP: " );
    M5.Lcd.println( SERVER_ADDRESS );
    M5.Lcd.print( "SERVER PORT: " );
    M5.Lcd.println( SERVER_PORT );
  } else {
    M5.Lcd.println( "\tIMPOSSIBLE to connect with server." );
    while ( 1 );  //it blocks here if server unavailable.
  }
  cy = M5.Lcd.getCursorY();
  eg = xEventGroupCreate();
  data = xQueueCreate( 5, BUFFER_LENGTH * 2 );
}


void loop() {
  int msgsize;
  if ( (msgsize = cmd_client.available()) > 0 ) {
    cmd_client.readBytes( cmd, msgsize );
    if ( ( cmd[0] == CMD_START ) && ( cmd[1] != 0 ) ) {
      M5.Lcd.setCursor(0, cy);
      M5.Lcd.println(" Started acquisition");
      M5.Lcd.printf(" Duration: %d s", cmd[1]);

      xTaskCreatePinnedToCore( & sendData, "SEND DATA", 4096, NULL, 5, NULL, 0);
      xTaskCreatePinnedToCore( & getDataT, "GET DATA", 4096, & cmd[1], 5, NULL, 1 );

      xEventGroupWaitBits( eg, EVENT_ACQ_END_BIT, pdTRUE, pdTRUE, portMAX_DELAY );
      M5.Lcd.fillRect(0, cy, M5.Lcd.width(), M5.Lcd.height()-cy, BLACK);
      M5.Lcd.setCursor( 0, cy );
      M5.Lcd.print("  Done ");
    } else if ( cmd[0] == CMD_PING ) {
      cmd_client.write( CMD_PING );
    } else if ( cmd[0] == CMD_WHEREISIT ){
      xTaskCreatePinnedToCore( &whereIsIt, "WHERE IS IT", 1024, NULL, 6, NULL, 1);
    }
    M5.Lcd.setCursor(0, M5.Lcd.height()-10);
    M5.Lcd.printf("%.0f%%", (M5.Axp.GetBatVoltage() - 3.3) * 100 / (4.2 - 3.3));
  }
  vTaskDelay( 1 / portTICK_PERIOD_MS );
}


void getDataT( void * uint8tTime) {
  TickType_t tTime = ( * ( ( uint8_t * ) uint8tTime) ) * 1000 * portTICK_PERIOD_MS;
  uint16_t samples[ BUFFER_LENGTH ];

  uint16_t usDelay = 1000000 / SAMPLING_FREQUENCY_HZ;

  TickType_t xLastWakeTime;
  unsigned long now = 0;

  xLastWakeTime = xTaskGetTickCount();
  //int k=0; // contatore buffers/pacchetti
  while ( xTaskGetTickCount() - xLastWakeTime  <= tTime ) {
    //Serial.print(k++);Serial.print('\t');Serial.println(xTaskGetTickCount() - xLastWakeTime);
    for ( int i = 0; i < BUFFER_LENGTH; i += 1 ) {
      while ( micros() - now <= usDelay );
      now = micros();
      samples[i] = analogRead( ADC_PIN );
      //Serial.println(now);
    }
    if ( xQueueSend( data, & samples, 0 ) != pdTRUE ) {
      // Serial.println("Queue full!");
    }
  }
  vTaskDelete( NULL );
}


void sendData( void * param ) {

  uint16_t samples[ BUFFER_LENGTH ];
  size_t sampleSize = sizeof( samples );

  while (1) {
    if ( xQueueReceive( data, & samples, 1000 / portTICK_PERIOD_MS ) == pdTRUE ) {
      cmd_client.write( ( uint8_t * ) samples, sampleSize );
    } else {
      // data has stopped to arrive
      cmd_client.write( CMD_STOP );
      vTaskDelay( 50 / portTICK_PERIOD_MS );
      xEventGroupSetBits( eg, EVENT_ACQ_END_BIT );
      vTaskDelete( NULL );
    }
  }
}

void whereIsIt(void * param){
  digitalWrite(LED_PIN, LOW); //il led ha logica invertita
  vTaskDelay(500 / portTICK_PERIOD_MS);
  digitalWrite(LED_PIN, HIGH);
  vTaskDelete(NULL);
}