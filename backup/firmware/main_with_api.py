"""
ESP32 Smart Parking - Tích hợp với Backend API
Gửi dữ liệu RFID lên server qua HTTP
"""

from machine import Pin, SPI, PWM
from mfrc522 import MFRC522
from lcd_i2c import LCD_I2C
import network
import urequests as requests
import ujson as json
import time

# ═══════════════════════════════════════════════════
# CẤU HÌNH
# ═══════════════════════════════════════════════════

# Wi-Fi
WIFI_SSID = "Thu Trinh 1"
WIFI_PASS = "phu760077"

# Backend API
API_BASE_URL = "http://192.168.1.233:8000/api/v1"  # Thay bằng IP máy tính của bạn
API_SCAN_ENDPOINT = "/rfid/scan"  # Endpoint nhận dữ liệu quét thẻ
GATE_ID = 1  # ID cổng này trong database

# ═══════════════════════════════════════════════════
# KHỞI TẠO PHẦN CỨNG
# ═══════════════════════════════════════════════════

# RFID Reader
spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(18), mosi=Pin(23), miso=Pin(19))
cs = Pin(5, Pin.OUT)
rst = Pin(4, Pin.OUT)
reader = MFRC522(spi, cs, rst)

# LED & Buzzer
led = Pin(2, Pin.OUT)
buzzer = Pin(13, Pin.OUT)

# Servo (cổng)
servo = PWM(Pin(14), freq=50)

# LCD I2C
try:
    lcd = LCD_I2C(i2c_addr=0x27, cols=16, rows=2)
except:
    try:
        lcd = LCD_I2C(i2c_addr=0x3F, cols=16, rows=2)
    except:
        lcd = None
        print("⚠️ LCD không khả dụng")

# Cảm biến siêu âm
trig = Pin(26, Pin.OUT)
echo = Pin(35, Pin.IN)

DISTANCE_THRESHOLD_CM = 30
GATE_OPEN_SEC = 5
COOLDOWN_MS = 2000

# ═══════════════════════════════════════════════════
# HÀM TIỆN ÍCH
# ═══════════════════════════════════════════════════

def connect_wifi():
    """Kết nối Wi-Fi"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print(f"Đang kết nối Wi-Fi: {WIFI_SSID}...")
        if lcd:
            lcd.show_message("Connecting WiFi", WIFI_SSID[:16])
        
        wlan.connect(WIFI_SSID, WIFI_PASS)
        
        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(".", end="")
        
        print()
    
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"✅ Đã kết nối! IP: {ip}")
        if lcd:
            lcd.show_message("WiFi Connected", ip)
        time.sleep(2)
        return True
    else:
        print("❌ Không thể kết nối Wi-Fi!")
        if lcd:
            lcd.show_message("WiFi Failed", "Check Config")
        return False

def get_distance():
    """Đo khoảng cách (cm)"""
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
    return d != -1 and d < DISTANCE_THRESHOLD_CM

def servo_angle(angle):
    """Điều khiển servo"""
    duty = int(25 + (angle / 180) * 102)
    servo.duty(duty)

def gate_open():
    """Mở cổng"""
    print("🔓 Mở cổng...")
    servo_angle(0)

def gate_close():
    """Đóng cổng"""
    print("🔒 Đóng cổng...")
    servo_angle(90)

def beep(freq=1000, duration_ms=100):
    """Phát âm thanh"""
    half_us = int(500_000 // freq)
    cycles = int((duration_ms * 1000) // (half_us * 2))
    for _ in range(cycles):
        buzzer.value(1)
        time.sleep_us(half_us)
        buzzer.value(0)
        time.sleep_us(half_us)

def beep_ok():
    """Âm thanh thành công"""
    beep(1500, 100)
    time.sleep_ms(80)
    beep(2000, 150)

def beep_err():
    """Âm thanh lỗi"""
    beep(400, 600)

def send_rfid_scan(card_uid, gate_id=GATE_ID):
    """
    Gửi dữ liệu quét thẻ lên backend
    Backend sẽ tự động:
    - Tạo customer mới nếu chưa có
    - Tạo vehicle mới nếu chưa có
    - Tạo/cập nhật RFID card
    - Tạo parking session
    """
    try:
        url = API_BASE_URL + API_SCAN_ENDPOINT
        
        payload = {
            "card_uid": card_uid,
            "gate_id": gate_id,
            "distance_cm": get_distance(),
            "timestamp": time.time()
        }
        
        print(f"📤 Gửi dữ liệu: {payload}")
        
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server phản hồi: {data}")
            return data
        else:
            print(f"❌ Lỗi server: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")
        return None

# ═══════════════════════════════════════════════════
# CHƯƠNG TRÌNH CHÍNH
# ═══════════════════════════════════════════════════

def main():
    print("=" * 50)
    print("  SMART PARKING - ESP32 RFID SYSTEM")
    print("=" * 50)
    print(f"✅ RFID Reader version: {hex(reader.version())}")
    
    # Kết nối Wi-Fi
    if not connect_wifi():
        print("⚠️ Chạy ở chế độ offline (không gửi dữ liệu)")
        wifi_connected = False
    else:
        wifi_connected = True
    
    # Đóng cổng ban đầu
    gate_close()
    
    if lcd:
        lcd.show_message(">>> READY <<<", "Scan RFID Card")
    
    print("\n--- HỆ THỐNG SẴN SÀNG ---")
    print("Vui lòng quẹt thẻ RFID...\n")
    
    last_uid = None
    last_time_ms = 0
    gate_is_open = False
    gate_open_at = 0
    
    try:
        while True:
            now = time.ticks_ms()
            
            # Tự động đóng cổng
            if gate_is_open and time.ticks_diff(now, gate_open_at) > GATE_OPEN_SEC * 1000:
                if is_someone_near():
                    gate_open_at = time.ticks_ms()
                    print("⚠ Có người gần cổng — giữ mở...")
                else:
                    gate_close()
                    if lcd:
                        lcd.show_message(">>> READY <<<", "Scan RFID Card")
                    gate_is_open = False
            
            # Quét thẻ RFID
            stat, tag = reader.request(reader.REQIDL)
            
            if stat == reader.OK:
                stat, uid = reader.anticoll()
                
                if stat == reader.OK and uid is not None:
                    now = time.ticks_ms()
                    
                    # Kiểm tra cooldown
                    if uid != last_uid or time.ticks_diff(now, last_time_ms) > COOLDOWN_MS:
                        card_id = "0x%02x%02x%02x%02x" % (uid[0], uid[1], uid[2], uid[3])
                        
                        print(f"\n🔍 Phát hiện thẻ: {card_id}")
                        
                        if lcd:
                            lcd.clear()
                            lcd.print("SCANNING...", 2, 0)
                            lcd.print(card_id[-8:], 4, 1)
                        
                        # Gửi lên server
                        if wifi_connected:
                            response = send_rfid_scan(card_id, GATE_ID)
                            
                            if response and response.get("success"):
                                # Server cho phép vào
                                action = response.get("action", "unknown")
                                customer_name = response.get("customer_name", "Guest")
                                vehicle_plate = response.get("vehicle_plate", "N/A")
                                
                                print(f"✅ Cho phép: {customer_name} - {vehicle_plate}")
                                print(f"   Hành động: {action}")
                                
                                if lcd:
                                    lcd.clear()
                                    lcd.print("WELCOME!", 4, 0)
                                    lcd.print(customer_name[:16], 0, 1)
                                
                                led.on()
                                beep_ok()
                                led.off()
                                
                                gate_open()
                                gate_is_open = True
                                gate_open_at = time.ticks_ms()
                            else:
                                # Server từ chối
                                print(f"❌ Từ chối: {response.get('message', 'Unknown error')}")
                                
                                if lcd:
                                    lcd.clear()
                                    lcd.print("ACCESS DENIED", 1, 0)
                                    lcd.print("Contact Admin", 1, 1)
                                
                                beep_err()
                        else:
                            # Chế độ offline - cho phép tất cả
                            print("⚠️ Chế độ offline - Cho phép vào")
                            
                            if lcd:
                                lcd.clear()
                                lcd.print("OFFLINE MODE", 2, 0)
                                lcd.print(card_id[-8:], 4, 1)
                            
                            led.on()
                            beep_ok()
                            led.off()
                            
                            gate_open()
                            gate_is_open = True
                            gate_open_at = time.ticks_ms()
                        
                        last_uid = uid
                        last_time_ms = now
                    
                    reader.halt()
            
            time.sleep_ms(100)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Dừng hệ thống...")
        gate_close()
        servo.deinit()
        if lcd:
            lcd.clear()
            lcd.show_message("System Stopped", "Goodbye!")
        print("✅ Đã dừng an toàn.")

# Chạy chương trình
if __name__ == "__main__":
    main()
