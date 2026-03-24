import paho.mqtt.client as mqtt
from database import Database

# Khởi tạo database
db = Database()

# Hàm xử lý khi kết nối thành công (API Version 2)
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Đã kết nối thành công với MQTT Broker!")
        client.subscribe("pbl5/parking/scan")
        client.subscribe("pbl5/parking/alert")
    else:
        print(f"❌ Kết nối thất bại, mã lỗi: {rc}")

# Hàm xử lý khi nhận tin nhắn
def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"📩 Topic: {msg.topic} | Nội dung: {payload}")

    if msg.topic == "pbl5/parking/scan":
        db.log_entry(payload, action="IN", fee=5000)
        print(f"💾 Đã lưu thẻ {payload} vào MongoDB.")

    elif msg.topic == "pbl5/parking/alert":
        db.log_alert(payload)
        print(f"⚠️ CẢNH BÁO KHẨN CẤP: {payload}")

# Khởi tạo client với API VERSION 2
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

# Kết nối đến Broker (Sử dụng HiveMQ công cộng để test)
print("🔗 Đang kết nối đến Broker...")
client.connect("broker.hivemq.com", 1883, 60)
client.loop_forever()