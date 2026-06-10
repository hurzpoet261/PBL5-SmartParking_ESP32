#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// ================= BẠN ĐIỀN WIFI Ở ĐÂY =================
const char* ssid = "t";
const char* password = "00000007";
// =======================================================

#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

httpd_handle_t camera_httpd = NULL;
httpd_handle_t stream_httpd = NULL;

// Camera quality profile:
// - /capture: sharper still image for OCR.
// - /stream: lower latency realtime preview for camera alignment.
// ESP32-CAM JPEG quality uses smaller number = better quality/larger file.
#define CAPTURE_FRAME_SIZE FRAMESIZE_VGA
#define CAPTURE_JPEG_QUALITY 12
#define STREAM_FRAME_SIZE FRAMESIZE_VGA
#define STREAM_JPEG_QUALITY 12
#define STREAM_FRAME_DELAY_MS 60
#define CAPTURE_SETTLE_DELAY_MS 40
#define STREAM_SETTLE_DELAY_MS 80

enum CameraProfile {
    PROFILE_UNKNOWN,
    PROFILE_CAPTURE,
    PROFILE_STREAM
};

static CameraProfile current_profile = PROFILE_UNKNOWN;

// MJPEG streaming config.
// Keep /capture for Python camera_bridge.py.
// Open stream at: http://<ESP32-CAM-IP>:81/stream
// If you do not want streaming, comment the stream server block in setup().
#define STREAM_BOUNDARY "123456789000000000000987654321"
static const char* STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" STREAM_BOUNDARY;
static const char* STREAM_BOUNDARY_LINE = "\r\n--" STREAM_BOUNDARY "\r\n";
static const char* STREAM_PART_HEADER = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

// API xử lý lệnh chụp ảnh tĩnh
static bool apply_capture_profile() {
    if (current_profile == PROFILE_CAPTURE) {
        return false;
    }

    sensor_t *s = esp_camera_sensor_get();
    if (!s) {
        return false;
    }

    s->set_framesize(s, CAPTURE_FRAME_SIZE);
    s->set_quality(s, CAPTURE_JPEG_QUALITY);
    current_profile = PROFILE_CAPTURE;
    return true;
}

static bool apply_stream_profile() {
    if (current_profile == PROFILE_STREAM) {
        return false;
    }

    sensor_t *s = esp_camera_sensor_get();
    if (!s) {
        return false;
    }

    s->set_framesize(s, STREAM_FRAME_SIZE);
    s->set_quality(s, STREAM_JPEG_QUALITY);
    current_profile = PROFILE_STREAM;
    return true;
}

static esp_err_t capture_handler(httpd_req_t *req) {
    Serial.println(">>> Nhận lệnh chụp ảnh từ Server! Đang xử lý...");
    camera_fb_t * fb = NULL;
    esp_err_t res = ESP_OK;

    // Chụp 1 tấm ảnh
    if (apply_capture_profile()) {
        delay(CAPTURE_SETTLE_DELAY_MS);
    }

    fb = esp_camera_fb_get();
    if (!fb) {
        Serial.println("LỖI: Chụp ảnh thất bại do phần cứng!");
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }

    // Cấu hình HTTP Header báo cho trình duyệt/Flask biết đây là file ảnh JPEG
    httpd_resp_set_type(req, "image/jpeg");
    httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");

    // Gửi mảng byte dữ liệu của bức ảnh đi
    res = httpd_resp_send(req, (const char *)fb->buf, fb->len);

    // CỰC KỲ QUAN TRỌNG: Giải phóng bộ nhớ RAM.
    esp_camera_fb_return(fb);

    Serial.println(">>> Đã gửi ảnh thành công!");
    return res;
}

// MJPEG stream endpoint for realtime camera alignment.
// This endpoint is not used by OCR. The Python bridge still uses /capture.
static esp_err_t stream_handler(httpd_req_t *req) {
    Serial.println(">>> Client connected to /stream");

    camera_fb_t *fb = NULL;
    esp_err_t res = ESP_OK;
    char part_buf[96];

    if (apply_stream_profile()) {
        delay(STREAM_SETTLE_DELAY_MS);
    }

    res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
    if (res != ESP_OK) {
        return res;
    }

    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_hdr(req, "X-Framerate", "10");

    while (true) {
        fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("ERROR: Stream frame capture failed!");
            res = ESP_FAIL;
            break;
        }

        size_t header_len = snprintf(part_buf, sizeof(part_buf), STREAM_PART_HEADER, fb->len);

        res = httpd_resp_send_chunk(req, STREAM_BOUNDARY_LINE, strlen(STREAM_BOUNDARY_LINE));
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, part_buf, header_len);
        }
        if (res == ESP_OK) {
            res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
        }

        esp_camera_fb_return(fb);
        fb = NULL;

        if (res != ESP_OK) {
            Serial.println(">>> Stream client disconnected");
            break;
        }

        // Limit FPS so WiFi/CPU stay available for /capture requests.
        vTaskDelay(STREAM_FRAME_DELAY_MS / portTICK_PERIOD_MS);
    }

    apply_capture_profile();
    return res;
}

void setup() {
    Serial.begin(115200);
    Serial.println("\nKhởi động hệ thống Smart Parking Camera...");

    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;  config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;  config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;  config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;  config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM; config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM; config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM; config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM; config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000; config.pixel_format = PIXFORMAT_JPEG;
    config.grab_mode = CAMERA_GRAB_LATEST;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    
    // TỐI ƯU CẤU HÌNH CHO OCR (Dành riêng cho máy ảnh cơ)
    // TỐI ƯU CẤU HÌNH CHO OCR (Dành riêng cho máy ảnh cơ)
    if(psramFound()){
        config.frame_size = CAPTURE_FRAME_SIZE;
        config.jpeg_quality = CAPTURE_JPEG_QUALITY;
        config.fb_count = 2;
    } else {
        Serial.println("Lỗi: Không tìm thấy PSRAM!");
        return;
    }

    if (esp_camera_init(&config) != ESP_OK) {
        Serial.println("Camera init failed!");
        return;
    }

    sensor_t * s = esp_camera_sensor_get();
    s->set_vflip(s, 1);
    s->set_brightness(s, 0);
    s->set_contrast(s, 1);
    s->set_saturation(s, 0);
    s->set_sharpness(s, 2);
    s->set_denoise(s, 1);
    s->set_quality(s, 10);
    s->set_whitebal(s, 1);
    s->set_awb_gain(s, 1);
    s->set_exposure_ctrl(s, 1);
    s->set_gain_ctrl(s, 1);
    apply_capture_profile();

    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500); Serial.print(".");
    }
    Serial.println("\nWiFi connected");

    httpd_config_t config_server = HTTPD_DEFAULT_CONFIG();
    config_server.server_port = 80;

    httpd_uri_t capture_uri = {
        .uri       = "/capture",
        .method    = HTTP_GET,
        .handler   = capture_handler,
        .user_ctx  = NULL
    };

    httpd_uri_t stream_uri = {
        .uri       = "/stream",
        .method    = HTTP_GET,
        .handler   = stream_handler,
        .user_ctx  = NULL
    };
    
    if (httpd_start(&camera_httpd, &config_server) == ESP_OK) {
        httpd_register_uri_handler(camera_httpd, &capture_uri);
        Serial.print("Snapshot API Ready! Lệnh chụp ảnh là: http://");
        Serial.print(WiFi.localIP());
        Serial.println("/capture");
    }

    // Streaming runs on port 81 so long-lived browser streams do not block /capture.
    // To go back to snapshot-only firmware, comment this block and upload again.
    httpd_config_t stream_server_config = HTTPD_DEFAULT_CONFIG();
    stream_server_config.server_port = 81;
    stream_server_config.ctrl_port = 32769;

    if (httpd_start(&stream_httpd, &stream_server_config) == ESP_OK) {
        httpd_register_uri_handler(stream_httpd, &stream_uri);
        Serial.print("Stream Ready! Open: http://");
        Serial.print(WiFi.localIP());
        Serial.println(":81/stream");
    }
}

void loop() {
    delay(10000); 
}
/*THÔNG SỐ SETUP CAMconfig.frame_size = FRAMESIZE_VGA
→ Độ phân giải: 640x480
config.jpeg_quality = 12
→ Chất lượng JPEG khá đẹp, cân bằng FPS
config.fb_count = 2
→ Double buffer, stream mượt hơn
config.grab_mode = CAMERA_GRAB_LATEST
→ Luôn lấy frame mới nhất, giảm delay
config.fb_location = CAMERA_FB_IN_PSRAM
→ Buffer nằm trong PSRAM
config.pixel_format = PIXFORMAT_JPEG
→ Stream MJPEG qua web
config.xclk_freq_hz = 20000000
→ XCLK = 20MHz
WiFi.setSleep(false)
→ Tắt sleep WiFi để giảm lag stream
WiFi.mode(WIFI_STA)
→ Chế độ station
Serial.begin(115200)
→ Baudrate serial 115200
s->set_vflip(s, 1)
→ Lật dọc ảnh
s->set_brightness(s, 0)
→ Brightness mặc định
s->set_contrast(s, 1)
→ Tăng contrast nhẹ
s->set_saturation(s, 0)
→ Saturation trung tính
s->set_sharpness(s, 2)
→ Tăng độ nét
s->set_denoise(s, 1)
→ Khử nhiễu nhẹ
s->set_quality(s, 10)
→ JPEG quality sensor-side tốt hơn
Sensor detect:
→ OV3660
Board config:
→ CAMERA_MODEL_AI_THINKER
Board Arduino IDE:
→ AI Thinker ESP32-CAM
Flash Frequency:
→ 80MHz
Partition Scheme:
→ Huge APP (3MB No OTA)
Upload Speed:
→ 115200
PSRAM:
→ Enabled
*/
