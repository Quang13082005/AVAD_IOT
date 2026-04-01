#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include <ESP32Servo.h>
#include "esp_timer.h"
#include "img_converters.h"
#include "Arduino.h"
#include <esp_http_server.h>

// ======================= WIFI & UDP CONFIG =======================
const char* ssid = "phuoc tuan";
const char* password = "bunlien123";
unsigned int localUdpPort = 12345;
WiFiUDP Udp;

// ======================= CAMERA MODEL CONFIG =====================
// CAMERA_MODEL_FREENOVE_WROVER (ESP32-S3)
#define PWDN_GPIO_NUM  -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM  15
#define SIOD_GPIO_NUM  4
#define SIOC_GPIO_NUM  5
#define Y9_GPIO_NUM    16
#define Y8_GPIO_NUM    17
#define Y7_GPIO_NUM    18
#define Y6_GPIO_NUM    12
#define Y5_GPIO_NUM    10
#define Y4_GPIO_NUM    8
#define Y3_GPIO_NUM    9
#define Y2_GPIO_NUM    11
#define VSYNC_GPIO_NUM 6
#define HREF_GPIO_NUM  7
#define PCLK_GPIO_NUM  13

// ======================= SERVO CONFIG =======================
// Tower A: PanA (360) and TiltA (180)
// Tower B: PanB (360) and TiltB (180)
Servo servoPanA;
Servo servoTiltA;
Servo servoPanB;
Servo servoTiltB;

const int pinPanA = 39;
const int pinTiltA = 40;
const int pinPanB = 41;
const int pinTiltB = 42;

// Shared variables for inter-core communication
volatile int targetPanA = 90;   // 360 Servo (Speed: 90 is stop)
volatile int targetTiltA = 90;  // 180 Servo (Angle)
volatile int targetPanB = 90;   // 360 Servo (Speed: 90 is stop)
volatile int targetTiltB = 90;  // 180 Servo (Angle)

// ======================= HTTP SERVER =======================
httpd_handle_t stream_httpd = NULL;

#define PART_BOUNDARY "123456789000000000000987654321"
static const char* _STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* _STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* _STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

esp_err_t stream_handler(httpd_req_t *req) {
    camera_fb_t * fb = NULL;
    esp_err_t res = ESP_OK;
    size_t _jpg_buf_len = 0;
    uint8_t * _jpg_buf = NULL;
    char * part_buf[64];
    res = httpd_resp_set_type(req, _STREAM_CONTENT_TYPE);
    if(res != ESP_OK) return res;

    while(true){
        fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("Camera capture failed");
            res = ESP_FAIL;
        } else {
            _jpg_buf_len = fb->len;
            _jpg_buf = fb->buf;
        }
        if(res == ESP_OK){
            size_t hlen = snprintf((char *)part_buf, 64, _STREAM_PART, _jpg_buf_len);
            res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
        }
        if(res == ESP_OK){
            res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
        }
        if(res == ESP_OK){
            res = httpd_resp_send_chunk(req, _STREAM_BOUNDARY, strlen(_STREAM_BOUNDARY));
        }
        if(fb){
            esp_camera_fb_return(fb);
            fb = NULL;
            _jpg_buf = NULL;
        } else if(_jpg_buf){
            free(_jpg_buf);
            _jpg_buf = NULL;
        }
        if(res != ESP_OK) break;
    }
    return res;
}

void startCameraServer() {
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 81;
    httpd_uri_t index_uri = {
        .uri       = "/stream",
        .method    = HTTP_GET,
        .handler   = stream_handler,
        .user_ctx  = NULL
    };
    if (httpd_start(&stream_httpd, &config) == ESP_OK) {
        httpd_register_uri_handler(stream_httpd, &index_uri);
        Serial.print("Camera Stream Ready on port 81: http://");
        Serial.print(WiFi.localIP());
        Serial.println(":81/stream");
    }
}

// ======================= STARTUP CALIBRATION =======================
void homingSequence() {
    Serial.println("--- BẮT ĐẦU HIỆU CHUẨN SERVO (CALIBRATION) ---");
    // 1. Tilt Servos (180): Di chuyển về giữa (90)
    servoTiltA.write(90);
    servoTiltB.write(90);
    delay(1000);
    
    // 2. Di chuyển Tilt sang các mức để kiểm tra cơ khí
    servoTiltA.write(60); servoTiltB.write(60); delay(500);
    servoTiltA.write(120); servoTiltB.write(120); delay(500);
    servoTiltA.write(90); servoTiltB.write(90); delay(500);
    
    // 3. Pan Servos (360): Xoay một chút để người dùng nhận biết
    // >90 là CW, <90 là CCW, 90 là đứng yên.
    servoPanA.write(95); servoPanB.write(95); delay(300); // Lưng chừng chậm về 1 hướng
    servoPanA.write(90); servoPanB.write(90); delay(500); // Dừng
    servoPanA.write(85); servoPanB.write(85); delay(300); // Ngược lại
    servoPanA.write(90); servoPanB.write(90); // Dừng hẳn
    
    Serial.println("--- HIỆU CHUẨN XONG. SERVO ĐÃ SẴN SÀNG ---");
}

// ======================= DUAL CORE TASKS =======================
void TaskComm(void *pvParameters) {
    // Core 0: WiFi + UDP
    Serial.print("Connecting to WiFi");
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi connected.");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());

    Udp.begin(localUdpPort);
    startCameraServer();

    char packetBuffer[255]; 
    while (true) {
        int packetSize = Udp.parsePacket();
        if (packetSize) {
            int len = Udp.read(packetBuffer, 255);
            if (len > 0) {
                packetBuffer[len] = '\0';
                // Ngôn ngữ giao tiếp: "PanASpeed,TiltAPos,PanBSpeed,TiltBPos" (vd: "92,90,88,120")
                int pa, ta, pb, tb;
                if (sscanf(packetBuffer, "%d,%d,%d,%d", &pa, &ta, &pb, &tb) == 4) {
                    targetPanA = pa;
                    targetTiltA = ta;
                    targetPanB = pb;
                    targetTiltB = tb;
                }
            }
        }
        delay(1); // Yield to watchdog
    }
}

void TaskServo(void *pvParameters) {
    // Core 1: Servo PWM Control
    while (true) {
        servoPanA.write(targetPanA);
        servoTiltA.write(targetTiltA);
        servoPanB.write(targetPanB);
        servoTiltB.write(targetTiltB);
        delay(20); // 50 Hz refresh rate loop
    }
}

// ======================= SETUP & LOOP =======================
void setup() {
    Serial.begin(115200);
    
    // Setup Servos (Use Timer 1 and 2 to leave Timer 0 for Camera)
    ESP32PWM::allocateTimer(1);
    ESP32PWM::allocateTimer(2);
    
    servoPanA.setPeriodHertz(50);
    servoTiltA.setPeriodHertz(50);
    servoPanB.setPeriodHertz(50);
    servoTiltB.setPeriodHertz(50);
    
    servoPanA.attach(pinPanA, 500, 2500);
    servoTiltA.attach(pinTiltA, 500, 2500);
    servoPanB.attach(pinPanB, 500, 2500);
    servoTiltB.attach(pinTiltB, 500, 2500);

    // Camera Init
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_7; // Avoid conflict with Servos
    config.ledc_timer = LEDC_TIMER_0;     // Camera uses Timer 0
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    
    if(psramFound()){
        config.frame_size = FRAMESIZE_VGA;
        config.jpeg_quality = 10;
        config.fb_count = 2;
    } else {
        config.frame_size = FRAMESIZE_SVGA;
        config.jpeg_quality = 12;
        config.fb_count = 1;
    }

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x", err);
        return;
    }

    // Call homing sequence
    homingSequence();

    // Start FreeRTOS Tasks
    xTaskCreatePinnedToCore(TaskComm, "TaskComm", 10000, NULL, 1, NULL, 0);
    xTaskCreatePinnedToCore(TaskServo, "TaskServo", 10000, NULL, 1, NULL, 1);
}

void loop() {
    // Loop gets blocked by FreeRTOS tasks. Nothing needed here.
    delay(1000);
}
