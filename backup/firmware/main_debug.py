"""
ESP32 Smart Parking - DEBUG VERSION
Có logging chi tiết để debug kết nối
"""

from machine import Pin, SPI, PWM
from mfrc522 import MFRC522
import network
import time

# ═══════════════════════════════════════════════════
# CẤU HÌNH
# ═══════════════════════════════════════════════════

WIFI_SSID = "Thu Trinh 1"
WIFI_PASS = "phu760077"
API_BASE_URL = "http://192.168.1.233:8000/api/v1"  # ⚠️ THAY ĐỔI IP NÀY
GATE_ID = 1

# ═══════════════════════════════════════════════════
# KHỞI TẠO PHẦN CỨNG
# ═══════════════════════════════════════════════════

print("=" * 50)
print("  ESP32 SMART PARKING - DEBUG MODE")
print("=" * 50)

# RFID Reader
spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(18), mosi=Pin(23), miso=Pin(19))
cs = Pin(5, Pin.OUT)
rst = Pin(4, Pin.OUT)
reader = MFRC522(spi, cs, rst)

print(f"✅ RFID Reader version: {hex(reader.version())}")

# LED & Buzzer
led = Pin(2, Pin.OUT)
buzzer = Pin(13, Pin.OUT)

# Servo
servo = PWM(Pin(14), freq=50)

def servo_angle(angle):
    duty = int(25 + (angle / 180) * 102)
    servo.duty(duty)

def gate_close():
    print("🔒 Đóng cổng")
    servo_angle(90)

def gate_open():
    print("🔓 Mở cổng")
    servo_angle(0)

def beep_ok():
    buzzer.value(1)
    time.sleep_ms(100)
    buzzer.value(0)

def beep_err():
    for _ in range(3):
        buzzer.value(1)
        time.sleep_ms(100)
        buzzer.value(0)
        time.sleep_ms(100)

gate_close()

# ═══════════════════════════════════════════════════
# KẾT NỐI WI-FI
# ═══════════════════════════════════════════════════

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"✅ Đã kết nối Wi-Fi: {ip}")
        return True
    
    print(f"\n📡 Đang kết nối Wi-Fi: {WIFI_SSID}")
    wlan.connect(WIFI_SSID, WIFI_PASS)
    
    timeout = 20
    while not wlan.isconnected() and timeout > 0:
        print(".", end="")
        time.sleep(1)
        timeout -= 1
    
    print()
    
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"✅ Kết nối thành công!")
        print(f"   IP: {ip}")
        print(f"   Gateway: {wlan.ifconfig()[2]}")
        return True
    else:
        print("❌ Không thể kết nối Wi-Fi!")
        print("   Kiểm tra SSID và password")
        return False

# ═══════════════════════════════════════════════════
# GỬI DỮ LIỆU LÊN SERVER
# ═══════════════════════════════════════════════════

def send_rfid_scan(card_uid):
    """Gửi dữ liệu quét thẻ lên backend"""
    try:
        # Import urequests ở đây để tránh lỗi nếu không có Wi-Fi
        import urequests as requests
        import ujson as json
        
        url = API_BASE_URL + "/rfid/scan"
        
        payload = {
            "card_uid": card_uid,
            "gate_id": GATE_ID,
            "distance_cm": 25.0,
            "timestamp": time.time()
        }
        
        print(f"\n📤 Gửi request đến: {url}")
        print(f"   Payload: {payload}")
        
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"📥 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Response data:")
            print(f"   Success: {data.get('success')}")
            print(f"   Action: {data.get('action')}")
            print(f"   Message: {data.get('message')}")
            print(f"   Customer: {data.get('customer_name')}")
            print(f"   Vehicle: {data.get('vehicle_plate')}")
            return data
        else:
            print(f"❌ Server error: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Lỗi kết nối: {e}")
        import sys
        sys.print_exception(e)
        return None

# ═══════════════════════════════════════════════════
# CHƯƠNG TRÌNH CHÍNH
# ═══════════════════════════════════════════════════

def main():
    print("\n" + "=" * 50)
    print("  BẮT ĐẦU CHƯƠNG TRÌNH")
    print("=" * 50)
    
    # Kết nối Wi-Fi
    wifi_connected = connect_wifi()
    
    if not wifi_connected:
        print("\n⚠️ Chạy ở chế độ OFFLINE")
        print("   Sẽ chỉ hiển thị UID thẻ, không gửi lên server")
    
    print("\n" + "=" * 50)
    print("  HỆ THỐNG SẴN SÀNG")
    print("=" * 50)
    print("Vui lòng quẹt thẻ RFID...\n")
    
    last_uid = None
    last_time_ms = 0
    COOLDOWN_MS = 3000  # 3 giây cooldown
    
    try:
        while True:
            now = time.ticks_ms()
            
            # Quét thẻ RFID
            stat, tag = reader.request(reader.REQIDL)
            
            if stat == reader.OK:
                stat, uid = reader.anticoll()
                
                if stat == reader.OK and uid is not None:
                    # Kiểm tra cooldown
                    if uid != last_uid or time.ticks_diff(now, last_time_ms) > COOLDOWN_MS:
                        card_id = "0x%02x%02x%02x%02x" % (uid[0], uid[1], uid[2], uid[3])
                        
                        print("\n" + "=" * 50)
                        print(f"🔍 PHÁT HIỆN THẺ: {card_id}")
                        print("=" * 50)
                        
                        led.on()
                        
                        if wifi_connected:
                            # Gửi lên server
                            response = send_rfid_scan(card_id)
                            
                            if response and response.get("success"):
                                print("\n✅ THÀNH CÔNG!")
                                beep_ok()
                                gate_open()
                                time.sleep(3)
                                gate_close()
                            else:
                                print("\n❌ THẤT BẠI!")
                                beep_err()
                        else:
                            # Chế độ offline
                            print("⚠️ Chế độ offline - Không gửi dữ liệu")
                            beep_ok()
                        
                        led.off()
                        
                        last_uid = uid
                        last_time_ms = now
                        
                        print("=" * 50)
                        print("Chờ thẻ tiếp theo...\n")
                    
                    reader.halt()
            
            time.sleep_ms(100)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Dừng hệ thống...")
        gate_close()
        servo.deinit()
        print("✅ Đã dừng an toàn.")

# Chạy chương trình
if __name__ == "__main__":
    main()
