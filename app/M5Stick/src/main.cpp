#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/semphr.h>
#include <freertos/queue.h>
#include <M5StickC.h>
#include "wifi_creds.h"       // WIFI AND TCP/IP CREDENTIALS 

/* SAMPLING_FREQUENCY
*   sampling frequency in HZ (up to 5 Khz)
*   TODO: remove define and set the sampling frequency when start acquisition
*         need to modify html too.
*/
#define SAMPLING_FREQUENCY_HZ     2000

/* BUFFER_LENGTH
*   the length of data packets
*   system acquire BUFFER_LENGTH data and send them over wifi
*/
#define BUFFER_LENGTH             64

/* COMMANDS
*   supported commands:
*     - CMD_START:      start acquisition, see getDataT and sendData functions,
      - CMD_PING:       to check connection status,   
      - CMD_WHEREISIT:  to check where this M5 is (phisically), see whereIsIt function
      - CMD_STOP:       to inform the server that acquisition is stopped
*/
#define CMD_START                 0x01
#define CMD_PING                  0x02
#define CMD_WHEREISIT             0x03
#define CMD_STOP                  "stop"
/* END COMMANDS */

#define LED_PIN                   10
#define ADC_PIN                   36

/*  EVENT_ACQ_END_BIT
*     bit to awake loop task when acquisition is ended
*/
#define EVENT_ACQ_END_BIT         ( 1 << 0 )

WiFiClient cmd_client;      // TCP/IP client

EventGroupHandle_t eg;      // Handles event groups "https://www.freertos.org/event-groups-API.html"
QueueHandle_t data;         // Queue of data buffers "https://www.freertos.org/a00018.html"

int16_t cy;                 // Y LCD coordinates to don't overwrite TCP/IP connection information.
uint8_t cmd[8];             // Received commands Buffer

/* Function prototypes */
void getDataT( void * uint8tTime );
void sendData( void * parameter );
void whereIsIt( void * parameter);
/* END Function prototypes */

void setup() {
  /* M5 INIT */
  M5.begin();               // inizializza anche la seriale a 115200 baud
  M5.Lcd.fillScreen( BLACK );
  M5.Lcd.setRotation( 3 );

  pinMode( ADC_PIN, INPUT );
  pinMode( LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);
  M5.Lcd.drawCircle( M5.Lcd.width() - 15, 7, 5, RED); // WiFi status (red: not conected, green: connected)
  M5.Lcd.setCursor( 5, 5 );

  /* WiFi SETUP */
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
  /* END WiFi SETUP */

  /* TCP/IP CONNECTION SETUP 
  *   M5 need that the server is up to go on
  */
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
  /* END TCP/IP CONNECTION SETUP */

  cy = M5.Lcd.getCursorY();
  eg = xEventGroupCreate();
  data = xQueueCreate( 5, BUFFER_LENGTH * 2 );
}


void loop() {
  int msgsize;
  if ( (msgsize = cmd_client.available()) > 0 ) {
    cmd_client.readBytes( cmd, msgsize );
    if ( ( cmd[0] == CMD_START ) && ( cmd[1] != 0 ) ) {                                // TODO: if 0 acquire forever
      /* DATA ACQUISITION*/
      M5.Lcd.setCursor(0, cy);
      M5.Lcd.println(" Started acquisition");
      M5.Lcd.printf(" Duration: %d s", cmd[1]);

      xTaskCreatePinnedToCore( & sendData, "SEND DATA", 4096, NULL, 5, NULL, 0);      // create data forwarding task
      xTaskCreatePinnedToCore( & getDataT, "GET DATA", 4096, & cmd[1], 5, NULL, 1 );  // create data acquisition task

      xEventGroupWaitBits( eg, EVENT_ACQ_END_BIT, pdTRUE, pdTRUE, portMAX_DELAY );    // sleep untill acquisition is done
      M5.Lcd.fillRect(0, cy, M5.Lcd.width(), M5.Lcd.height()-cy, BLACK);
      M5.Lcd.setCursor( 0, cy );
      M5.Lcd.print("  Done ");
      /* END DATA ACQUISITION */
    } else if ( cmd[0] == CMD_PING ) {
      /* SERVER IS WAITING FOR RESPONSE. IF M5 DON'T PONG THE SERVER
      *    IN 3 SECONDS SERVER WILL ASSUME THAT CONNECTION IS LOST ( see client.py$Client#ping )
      */
      cmd_client.write( CMD_PING );
    } else if ( cmd[0] == CMD_WHEREISIT ){
      xTaskCreatePinnedToCore( &whereIsIt, "WHERE IS IT", 1024, NULL, 6, NULL, 1);
    }
    M5.Lcd.setCursor(0, M5.Lcd.height()-10);
    M5.Lcd.printf("%.0f%%", (M5.Axp.GetBatVoltage() - 3.3) * 100 / (4.2 - 3.3));
  }
  vTaskDelay( 1 / portTICK_PERIOD_MS );
}

/* getDataT
*   FreeRTOS task for acquisition from ADC_PIN.
*   Fills Queue buffers while sendData task empties
*
*   PARAMS:
*     - void * uint8tTime: seconds of acquisition time 
*
*   TODO: 
*     - Make the param a data structure so we can pass time and sampling frequency
*     - If acquisition time is 0 we can assume that we want to get get data forever.
*         While M5 is getting data we need to send commands too, so we need a non blocking function and 
*         probably another TCP/IP client because cmd_client is engaged in data forwarding
*/
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
      /* IF 0 <= SAMPLING_FREQUENCY_HZ <= 5000 YOU SHOULD NEVER GO INSIDE HERE */
      // Serial.println("Queue full!");
    }
  }
  vTaskDelete( NULL );
}

/* sendData
*   FreeRTOS task for data wifi forwarding.
*   Read Queue buffers and send packets over WiFi usind cmd_client (TCP/IP client)
*/
void sendData( void * param ) {

  uint16_t samples[ BUFFER_LENGTH ];
  size_t sampleSize = sizeof( samples );

  while (1) {
    if ( xQueueReceive( data, & samples, 1000 / portTICK_PERIOD_MS ) == pdTRUE ) {
      cmd_client.write( ( uint8_t * ) samples, sampleSize );
    } else {
      // data has stopped to arrive
      cmd_client.write( CMD_STOP );                   // Informs server that acquisition is done
      vTaskDelay( 50 / portTICK_PERIOD_MS );
      xEventGroupSetBits( eg, EVENT_ACQ_END_BIT );    // Set bit to awake loop.
      vTaskDelete( NULL );
    }
  }
}

/* whereIsIt
*   FreeRTOS task to blink M5 embedded LED for 500 ms 
*/
void whereIsIt(void * param){
  digitalWrite(LED_PIN, LOW); // inverse logic for M5 embedded LED
  vTaskDelay(500 / portTICK_PERIOD_MS);
  digitalWrite(LED_PIN, HIGH);
  vTaskDelete(NULL);
}