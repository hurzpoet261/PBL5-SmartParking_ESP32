"""
ESP32 Smart Parking - Main Program
Firmware hoàn chỉnh với kết nối Wi-Fi ổn định và logic chặt chẽ
"""

from machine import Pin, SPI, PWM
from mfrc522 import MFRC522
from lcd_i2c import LCD_I2C
import network
import time
import esp32_config as config

# ═══════════════════════════════════════════════════
# KHỞI TẠO PHẦN CỨNG
# ═══════════════════════════════════════════════════

print("=" * 60)
print("  ESP32 SMART PARKING SYSTEM")
print("  Version: 2.0")
print("=" * 60)

# RFID Reader
spi = SPI(1, baudrate=config.RFID_SPI_BAUDRATE, polarity=0, phase=0,
          sck=Pin(config.RFID_SCK_PIN), 
          mosi=Pin(config.RFID_MOSI_PIN), 
          miso=Pin(config.RFID_MISO_PIN))
cs = Pin(config.RFID_CS_PIN, Pin.OUT)
rst = Pin(config.RFID_RST_PIN, Pin.OUT)
reader = MFRC522(spi, cs, rst)

config.log(f"✅ RFID Reader initialized: {hex(reader.version())}")

# LED & Buzzer
led = Pin(config.LED_PIN, Pin.OUT)
buzzer = Pin(config.BUZZER_PIN, Pin.OUT)

# Servo
servo = PWM(Pin(config.SERVO_PIN), freq=config.SERVO_FREQ)

# Ultrasonic Sensor
trig = Pin(config.ULTRASONIC_TRIG_PIN, Pin.OUT)
echo = Pin(config.ULTRASONIC_ECHO_PIN, Pin.IN)

# LCD Display
lcd = None
try:
    lcd = LCD_I2C(i2c_addr=config.LCD_I2C_ADDR, cols=config.LCD_COLS, rows=config.LCD_ROWS)
    config.log("✅ LCD initialized")
except:
    try:
        lcd = LCD_I2C(i2c_addr=0x3F, cols=config.LCD_COLS, rows=config.LCD_ROWS)
        config.log("✅ LCD initialized (address 0x3F)")
    except:
        config.log("⚠️ LCD not available")

# ═══════════════════════════════════════════════════
# HARDWARE CONTROL FUNCTIONS
# ═══════════════════════════════════════════════════

def servo_angle(angle):
    """Điều khiển góc servo"""
    duty = int(25 + (angle / 180) * 102)
    servo.duty(duty)

def gate_open():
    """Mở cổng"""
    config.log(f"🔓 Mở cổng: {config.GATE_NAME}")
    servo_angle(config.SERVO_ANGLE_OPEN)
    if lcd:
        lcd.show_message("GATE OPENING", config.GATE_NAME)

def gate_close():
    """Đóng cổng"""
    config.log(f"🔒 Đóng cổng: {config.GATE_NAME}")
    servo_angle(config.SERVO_ANGLE_CLOSE)

def get_distance():
    """Đo khoảng cách bằng cảm biến siêu âm (cm)"""
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)
    
    timeout = time.ticks_us()
    while echo.value() == 0:
        if time.ticks_diff(time.ticks_us(), timeout) > 30_000:
            return -1
    
    start = time.ticks_us()
    while echo.value() == 1:
        if time.ticks_diff(time.ticks_us(), start) > 30_000:
            return -1
    
    duration = time.ticks_diff(time.ticks_us(), start)
    distance = (duration * 0.0343) / 2
    return round(distance, 1)

def is_someone_near():
    """Kiểm tra có người gần cổng không"""
    d = get_distance()
    return d != -1 and d < config.ULTRASONIC_THRESHOLD_CM

def beep(freq, duration_ms):
    """Phát âm thanh"""
    half_us = int(500_000 // freq)
    cycles = int((duration_ms * 1000) // (half_us * 2))
    for _ in range(cycles):
        buzzer.value(1)
        time.sleep_us(half_us)
        buzzer.value(0)
        time.sleep_us(half_us)

def beep_success():
    """Âm thanh thành công"""
    beep(config.BEEP_SUCCESS_FREQ, config.BEEP_SUCCESS_DURATION)
    time.sleep_ms(80)
    beep(config.BEEP_SUCCESS_FREQ + 500, config.BEEP_SUCCESS_DURATION + 50)

def beep_error():
    """Âm thanh lỗi"""
    beep(config.BEEP_ERROR_FREQ, config.BEEP_ERROR_DURATION)

def display_message(line1, line2=""):
    """Hiển thị message trên LCD"""
    if lcd:
        lcd.show_message(line1, line2)

# ═══════════════════════════════════════════════════
# WI-FI CONNECTION
# ═══════════════════════════════════════════════════

def connect_wifi():
    """Kết nối Wi-Fi với retry logic"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        config.log(f"✅ Already connected: {ip}")
        if config.DEBUG_SHOW_WIFI_INFO:
            config.log(f"   Gateway: {wlan.ifconfig()[2]}")
            config.log(f"   DNS: {wlan.ifconfig()[3]}")
        return True
    
    config.log(f"\n📡 Connecting to Wi-Fi: {config.WIFI_SSID}")
    display_message(config.MSG_CONNECTING, config.WIFI_SSID[:16])
    
    wlan.connect(config.WIFI_SSID, config.WIFI_PASS)
    
    timeout = config.WIFI_TIMEOUT
    while not wlan.isconnected() and timeout > 0:
        print(".", end="")
        time.sleep(1)
        timeout -= 1
    
    print()
    
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        config.log(f"✅ Wi-Fi connected successfully!")
        config.log(f"   IP Address: {ip}")
        
        if config.DEBUG_SHOW_WIFI_INFO:
            config.log(f"   Subnet Mask: {wlan.ifconfig()[1]}")
            config.log(f"   Gateway: {wlan.ifconfig()[2]}")
            config.log(f"   DNS: {wlan.ifconfig()[3]}")
            config.log(f"   Signal Strength: {wlan.status('rssi')} dBm")
        
        display_message(config.MSG_WIFI_OK, ip)
        time.sleep(2)
        return True
    else:
        config.log("❌ Wi-Fi connection failed!")
        config.log(f"   SSID: {config.WIFI_SSID}")
        config.log("   Please check:")
        config.log("   1. SSID and password are correct")
        config.log("   2. Wi-Fi is 2.4GHz (ESP32 doesn't support 5GHz)")
        config.log("   3. Wi-Fi router is powered on")
        
        display_message(config.MSG_WIFI_FAIL, "Check Config")
        return False

def check_wifi_connection():
    """Kiểm tra và tự động kết nối lại Wi-Fi nếu mất kết nối"""
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        config.log("⚠️ Wi-Fi disconnected! Reconnecting...")
        return connect_wifi()
    return True

# ═══════════════════════════════════════════════════
# API COMMUNICATION
# ═══════════════════════════════════════════════════

def send_rfid_scan(card_uid):
    """Gửi dữ liệu quét thẻ lên backend API"""
    try:
        import urequests as requests
        import ujson as json
        
        url = config.get_api_endpoint("/rfid/scan")
        
        payload = {
            "card_uid": card_uid,
            "gate_id": config.GATE_ID,
            "distance_cm": get_distance(),
            "timestamp": time.time()
        }
        
        if config.DEBUG_SHOW_API_REQUEST:
            config.log(f"\n📤 API Request:")
            config.log(f"   URL: {url}")
            config.log(f"   Payload: {payload}")
        
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=config.API_TIMEOUT
        )
        
        if config.DEBUG_SHOW_API_REQUEST:
            config.log(f"📥 API Response:")
            config.log(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if config.DEBUG_SHOW_API_REQUEST:
                config.log(f"   Data: {data}")
            
            return data
        else:
            config.log(f"❌ API Error: {response.status_code}")
            config.log(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        config.log(f"❌ API Connection Error: {e}")
        return None

# ═══════════════════════════════════════════════════
# RFID CARD PROCESSING
# ═══════════════════════════════════════════════════

def process_rfid_card(card_uid, wifi_connected):
    """Xử lý thẻ RFID đã quét"""
    try: 
        config.log(f"\n{'=' * 60}")
        config.log(f"🔍 RFID Card Detected: {card_uid}")
        config.log(f"{'=' * 60}")
        
        led.on()
        display_message(config.MSG_SCANNING, card_uid[-8:])
        
        if wifi_connected:
            # Online mode - Gửi lên server
            response = send_rfid_scan(card_uid)
            
            if response and response.get("success"):
                # Server cho phép
                action = response.get("action", "unknown")
                customer_name = response.get("customer_name", "Guest")
                vehicle_plate = response.get("vehicle_plate", "N/A")
                message = response.get("message", "")
                
                config.log(f"✅ Access Granted!")
                config.log(f"   Action: {action}")
                config.log(f"   Customer: {customer_name}")
                config.log(f"   Vehicle: {vehicle_plate}")
                config.log(f"   Message: {message}")
                
                display_message(config.MSG_ACCEPTED, customer_name[:16])
                beep_success()
                
                gate_open()
                return True
            else:
                # Server từ chối hoặc lỗi
                config.log(f"❌ Access Denied!")
                if response:
                    config.log(f"   Reason: {response.get('message', 'Unknown')}")
                
                display_message(config.MSG_DENIED, "Contact Admin")
                beep_error()
                return False
        else:
            # Offline mode
            if config.OFFLINE_MODE_ENABLED:
                if config.OFFLINE_ALLOW_ALL_CARDS or card_uid in config.OFFLINE_AUTHORIZED_CARDS:
                    config.log(f"✅ Offline Mode - Access Granted")
                    display_message(config.MSG_OFFLINE, card_uid[-8:])
                    beep_success()
                    gate_open()
                    return True
                else:
                    config.log(f"❌ Offline Mode - Card Not Authorized")
                    display_message(config.MSG_DENIED, "Not Authorized")
                    beep_error()
                    return False
            else:
                config.log(f"❌ Offline Mode Disabled")
                display_message(config.MSG_ERROR, "No Connection")
                beep_error()
                return False
    
    finally:
        led.off()

# ═══════════════════════════════════════════════════
# MAIN PROGRAM
# ═══════════════════════════════════════════════════

def main():
    """Chương trình chính"""
    config.log("\n" + "=" * 60)
    config.log("  STARTING SMART PARKING SYSTEM")
    config.log("=" * 60)
    
    # Đóng cổng ban đầu
    gate_close()
    
    # Kết nối Wi-Fi
    wifi_connected = connect_wifi()
    
    if not wifi_connected:
        if config.OFFLINE_MODE_ENABLED:
            config.log("\n⚠️ Running in OFFLINE MODE")
            config.log("   Only authorized cards will be accepted")
        else:
            config.log("\n❌ Cannot start without Wi-Fi connection")
            display_message(config.MSG_ERROR, "No WiFi")
            return
    
    # Hiển thị ready message
    display_message(config.MSG_WELCOME, config.MSG_SCAN_CARD)
    
    config.log("\n" + "=" * 60)
    config.log("  SYSTEM READY")
    config.log("=" * 60)
    config.log("Waiting for RFID cards...\n")
    
    # State variables
    last_uid = None
    last_time_ms = 0
    gate_is_open = False
    gate_open_at = 0
    wifi_check_counter = 0
    
    try:
        while True:
            now = time.ticks_ms()
            
            # Kiểm tra Wi-Fi định kỳ (mỗi 30 giây)
            wifi_check_counter += 1
            if wifi_check_counter >= 300:  # 300 * 100ms = 30s
                wifi_connected = check_wifi_connection()
                wifi_check_counter = 0
            
            # Tự động đóng cổng
            if gate_is_open and config.GATE_AUTO_CLOSE:
                elapsed = time.ticks_diff(now, gate_open_at)
                if elapsed > config.GATE_OPEN_DURATION * 1000:
                    if is_someone_near():
                        # Có người → giữ cổng mở
                        gate_open_at = time.ticks_ms()
                        config.log("⚠️ Person detected - keeping gate open")
                    else:
                        # Không còn ai → đóng cổng
                        gate_close()
                        display_message(config.MSG_WELCOME, config.MSG_SCAN_CARD)
                        gate_is_open = False
            
            # Quét thẻ RFID
            stat, tag = reader.request(reader.REQIDL)
            
            if stat == reader.OK:
                stat, uid = reader.anticoll()
                
                if stat == reader.OK and uid is not None:
                    # Kiểm tra cooldown
                    if uid != last_uid or time.ticks_diff(now, last_time_ms) > config.SCAN_COOLDOWN_MS:
                        card_id = "0x%02x%02x%02x%02x" % (uid[0], uid[1], uid[2], uid[3])
                        
                        # Xử lý thẻ
                        access_granted = process_rfid_card(card_id, wifi_connected)
                        
                        if access_granted:
                            gate_is_open = True
                            gate_open_at = time.ticks_ms()
                        
                        last_uid = uid
                        last_time_ms = now
                        
                        config.log("=" * 60)
                        config.log("Waiting for next card...\n")
                    
                    reader.halt()
            
            time.sleep_ms(100)
    
    except KeyboardInterrupt:
        config.log("\n\n🛑 System stopped by user")
        gate_close()
        servo.deinit()
        display_message("System Stopped", "Goodbye!")
        config.log("✅ Shutdown complete")

# ═══════════════════════════════════════════════════
# START PROGRAM
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    main()
