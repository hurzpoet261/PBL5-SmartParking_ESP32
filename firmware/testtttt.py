import machine
import time
import network
from machine import Pin, SPI, PWM
from mfrc522 import MFRC522
from umqtt_simple import MQTTClient
import config

# --- KHỞI TẠO CẤU HÌNH ---

# Cấu hình Servo (Chân 13)
servo = PWM(Pin(13), freq=50)

# Cấu hình Buzzer (Chân 14) - Sử dụng PWM để tạo tiếng kêu thanh hơn
buzzer_pwm = PWM(Pin(14))
buzzer_pwm.duty(0) # Tắt còi lúc đầu

# Cấu hình Gas Sensor (Chân 34)
gas_sensor = Pin(34, Pin.IN)

# Khởi tạo RFID (SPI 2)
spi = SPI(2, baudrate=2500000, sck=Pin(18), mosi=Pin(23), miso=Pin(19))
rdr = MFRC522(spi, gpioRst=2, gpioCs=15)

def beep(duration=0.2):
    """Hàm làm còi kêu tít một cái"""
    buzzer_pwm.freq(1000)
    buzzer_pwm.duty(512)
    time.sleep(duration)
    buzzer_pwm.duty(0)

def connect_wifi():
    print(" đang kết nối WiFi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(config.WIFI_SSID, config.WIFI_PASS)
    while not wlan.isconnected():
        time.sleep(0.5)
        print(".", end="")
    print("\n✅ WiFi Connected!")
    print("🏠 IP Address:", wlan.ifconfig()[0])

def open_gate():
    print("🔓 Đang mở cổng...")
    servo.duty(40)  # Góc mở
    time.sleep(3)
    print("🔒 Đang đóng cổng...")
    servo.duty(115) # Góc đóng

# --- CHƯƠNG TRÌNH CHÍNH ---

connect_wifi()

try:
    client = MQTTClient("esp32_huy", config.MQTT_BROKER)
    client.connect()
    print("✅ MQTT Broker Connected!")
except:
    print("❌ Lỗi kết nối MQTT. Kiểm tra Broker hoặc WiFi!")

print("🚀 SYSTEM READY - Đang đợi quét thẻ...")

last_gas_log = 0

while True:
    current_time = time.time()
    gas_value = gas_sensor.value()
    
    # 1. Log trạng thái Gas ra Terminal mỗi 5 giây
    if current_time - last_gas_log >= 5:
        gas_status = "NGUY HIỂM (CÓ GAS)" if gas_value == 1 else "AN TOÀN"
        print(f"🌡️ [SENSOR]: Trạng thái Gas: {gas_status}")
        last_gas_log = current_time
        
        if gas_value == 1:
            print("⚠️ Gửi cảnh báo Gas lên Server!")
            try:
                client.publish(config.MQTT_TOPIC_ALERT, "GAS_WARNING")
            except:
                pass
            beep(1) # Kêu còi dài khi có gas
    
    # 2. Quét thẻ RFID
    (stat, tag_type) = rdr.request(rdr.REQIDL)
    if stat == rdr.OK:
        (stat, raw_uid) = rdr.anticoll()
        if stat == rdr.OK and raw_uid is not None:
            # Chuyển đổi UID thành chuỗi hex
            card_id = "0x%02x%02x%02x%02x" % (raw_uid[0], raw_uid[1], raw_uid[2], raw_uid[3])
            
            print("-" * 30)
            print(f"💳 PHÁT HIỆN THẺ: {card_id}")
            
            # Kêu còi tít một cái
            beep(0.2)
            
            # Gửi MQTT và mở cửa
            print(f"📤 Gửi ID thẻ lên Topic: {config.MQTT_TOPIC_SCAN}")
            try:
                client.publish(config.MQTT_TOPIC_SCAN, card_id)
                open_gate()
            except:
                print("❌ Lỗi: Không gửi được dữ liệu MQTT!")
            
            print("-" * 30)
            
            # Đợi để tránh đọc liên tục một thẻ
            time.sleep(2)
    
    time.sleep(0.1)