"""
ESP32 Smart Parking - Configuration File
Cấu hình tập trung cho toàn bộ hệ thống ESP32
"""

# ═══════════════════════════════════════════════════
# WI-FI CONFIGURATION
# ═══════════════════════════════════════════════════

WIFI_SSID = "Thu Trinh 1"           # ⚠️ THAY ĐỔI: Tên Wi-Fi của bạn
WIFI_PASS = "phu760077"             # ⚠️ THAY ĐỔI: Mật khẩu Wi-Fi
WIFI_TIMEOUT = 20                    # Timeout kết nối (giây)
WIFI_RETRY_DELAY = 5                 # Delay giữa các lần thử lại (giây)

# ═══════════════════════════════════════════════════
# BACKEND API CONFIGURATION
# ═══════════════════════════════════════════════════

API_BASE_URL = "http://192.168.1.235:8000/api/v1"  # ⚠️ THAY ĐỔI: IP máy tính chạy backend
API_TIMEOUT = 10                     # Timeout cho API request (giây)
API_RETRY = 3                        # Số lần thử lại khi lỗi

# ═══════════════════════════════════════════════════
# GATE CONFIGURATION
# ═══════════════════════════════════════════════════

GATE_ID = 1                          # ID cổng trong database
GATE_NAME = "Cổng chính"            # Tên cổng
GATE_OPEN_DURATION = 5               # Thời gian mở cổng (giây)
GATE_AUTO_CLOSE = True               # Tự động đóng cổng

# ═══════════════════════════════════════════════════
# HARDWARE PIN CONFIGURATION
# ═══════════════════════════════════════════════════

# RFID Reader (MFRC522) - SPI
RFID_SCK_PIN = 18
RFID_MOSI_PIN = 23
RFID_MISO_PIN = 19
RFID_CS_PIN = 5
RFID_RST_PIN = 4
RFID_SPI_BAUDRATE = 1_000_000

# Servo Motor (Gate Control)
SERVO_PIN = 14
SERVO_FREQ = 50
SERVO_ANGLE_OPEN = 0                 # Góc mở cổng
SERVO_ANGLE_CLOSE = 90               # Góc đóng cổng

# LED Indicator
LED_PIN = 2

# Buzzer
BUZZER_PIN = 13

# Ultrasonic Sensor (HC-SR04)
ULTRASONIC_TRIG_PIN = 26
ULTRASONIC_ECHO_PIN = 35
ULTRASONIC_THRESHOLD_CM = 30         # Khoảng cách phát hiện người (cm)

# LCD I2C Display
LCD_I2C_ADDR = 0x27                  # Địa chỉ I2C (thử 0x3F nếu không hoạt động)
LCD_SDA_PIN = 21
LCD_SCL_PIN = 22
LCD_COLS = 16
LCD_ROWS = 2

# ═══════════════════════════════════════════════════
# RFID SCAN CONFIGURATION
# ═══════════════════════════════════════════════════

SCAN_COOLDOWN_MS = 3000              # Thời gian chờ giữa 2 lần quét (ms)
SCAN_RETRY_ON_ERROR = True           # Thử lại khi lỗi API

# ═══════════════════════════════════════════════════
# DISPLAY MESSAGES
# ═══════════════════════════════════════════════════

MSG_WELCOME = ">>> READY <<<"
MSG_SCAN_CARD = "Scan RFID Card"
MSG_CONNECTING = "Connecting..."
MSG_WIFI_OK = "WiFi Connected"
MSG_WIFI_FAIL = "WiFi Failed"
MSG_SCANNING = "SCANNING..."
MSG_ACCEPTED = "WELCOME!"
MSG_DENIED = "ACCESS DENIED"
MSG_ERROR = "ERROR"
MSG_OFFLINE = "OFFLINE MODE"

# ═══════════════════════════════════════════════════
# BUZZER SOUNDS
# ═══════════════════════════════════════════════════

BEEP_SUCCESS_FREQ = 1500
BEEP_SUCCESS_DURATION = 100
BEEP_ERROR_FREQ = 400
BEEP_ERROR_DURATION = 600

# ═══════════════════════════════════════════════════
# DEBUG CONFIGURATION
# ═══════════════════════════════════════════════════

DEBUG_MODE = True                    # Bật/tắt debug logging
DEBUG_SHOW_WIFI_INFO = True          # Hiển thị thông tin Wi-Fi
DEBUG_SHOW_API_REQUEST = True        # Hiển thị API request/response
DEBUG_SHOW_RFID_UID = True           # Hiển thị UID thẻ RFID

# ═══════════════════════════════════════════════════
# OFFLINE MODE
# ═══════════════════════════════════════════════════

OFFLINE_MODE_ENABLED = True          # Cho phép hoạt động offline
OFFLINE_ALLOW_ALL_CARDS = False      # Cho phép tất cả thẻ khi offline
OFFLINE_AUTHORIZED_CARDS = [         # Danh sách thẻ được phép (offline)
    "0xa3d6ce05",
    "0xcc40d906",
    "0xd5a810ec",
]

# ═══════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════

def get_api_endpoint(endpoint):
    """Lấy URL đầy đủ của endpoint"""
    return f"{API_BASE_URL}{endpoint}"

def is_debug():
    """Kiểm tra debug mode"""
    return DEBUG_MODE

def log(message):
    """Log message nếu debug mode bật"""
    if DEBUG_MODE:
        print(message)
