from machine import Pin, SPI, PWM
from mfrc522 import MFRC522
import time

# ── Phần cứng ──────────────────────────────────────
spi    = SPI(1, baudrate=1_000_000, polarity=0, phase=0,
             sck=Pin(18), mosi=Pin(23), miso=Pin(19))
cs     = Pin(5,  Pin.OUT)
rst    = Pin(4,  Pin.OUT)
reader = MFRC522(spi, cs, rst)
led    = Pin(2,  Pin.OUT)
buzzer = Pin(13, Pin.OUT)
servo  = PWM(Pin(14), freq=50)

# ── Cảm biến siêu âm ────────────────────────────────
# ⚠️ GPIO34 là INPUT-ONLY → đổi TRIG sang GPIO26
trig = Pin(26, Pin.OUT)   # ← Đổi từ 34 sang 26
echo = Pin(35, Pin.IN)    # ← GPIO35 OK vì là INPUT

DISTANCE_THRESHOLD_CM = 9  # Phát hiện người trong vòng 30cm

def get_distance():
    """Đo khoảng cách bằng HC-SR04, trả về cm. -1 nếu timeout."""
    # Pulse TRIG 10µs
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)

    # Đo thời gian ECHO HIGH
    timeout = time.ticks_us()
    while echo.value() == 0:
        if time.ticks_diff(time.ticks_us(), timeout) > 30_000:
            return -1  # Timeout chờ ECHO lên

    start = time.ticks_us()
    while echo.value() == 1:
        if time.ticks_diff(time.ticks_us(), start) > 30_000:
            return -1  # Timeout chờ ECHO xuống

    duration = time.ticks_diff(time.ticks_us(), start)
    distance = (duration * 0.0343) / 2
    return round(distance, 1)

def is_someone_near():
    d = get_distance()
    if d == -1:
        return False
    return d < DISTANCE_THRESHOLD_CM

# ── Servo ───────────────────────────────────────────
def servo_angle(angle):
    duty = int(25 + (angle / 180) * 102)
    servo.duty(duty)

def gate_open():
    print("🔓 Mở cổng...")
    servo_angle(0)

def gate_close():
    print("🔒 Đóng cổng...")
    servo_angle(90)

# ── Buzzer ──────────────────────────────────────────
def beep(freq=1000, duration_ms=100):
    half_us = int(500_000 // freq)
    cycles  = int((duration_ms * 1000) // (half_us * 2))
    for _ in range(cycles):
        buzzer.value(1)
        time.sleep_us(half_us)
        buzzer.value(0)
        time.sleep_us(half_us)

def beep_ok():
    beep(1500, 100)
    time.sleep_ms(80)
    beep(2000, 150)

def beep_err():
    beep(400, 600)

# ── Khởi tạo ────────────────────────────────────────

print("✅ Chip version:", hex(reader.version()))
gate_close()

# ── Danh sách thẻ hợp lệ ────────────────────────────
AUTHORIZED = [
    "0xa3d6ce05",
    "0xcc40d906",
]

GATE_OPEN_SEC = 3  # Thời gian mở cổng tối thiểu

# ── Vòng lặp chính ──────────────────────────────────
print("--- HỆ THỐNG KIỂM SOÁT VÀO RA ---")
print("Vui lòng quẹt thẻ RFID...")

last_uid     = None
last_time_ms = 0
COOLDOWN_MS  = 2000
gate_is_open = False
gate_open_at = 0

try:
    while True:
        now = time.ticks_ms()

        # ✅ Tự động đóng cổng — CHỈ đóng khi không còn ai
        if gate_is_open and time.ticks_diff(now, gate_open_at) > GATE_OPEN_SEC * 1000:
            if is_someone_near():
                # Có người → giữ cổng mở, reset timer
                gate_open_at = time.ticks_ms()
                print("⚠ Có người gần cổng — giữ mở...")
            else:
                # Không còn ai → đóng cổng
                gate_close()
                gate_is_open = False

        # ── Quét thẻ ──────────────────────────────────
        stat, tag = reader.request(reader.REQIDL)

        if stat == reader.OK:
            stat, uid = reader.anticoll()

            if stat == reader.OK and uid is not None:
                now = time.ticks_ms()

                if uid != last_uid or time.ticks_diff(now, last_time_ms) > COOLDOWN_MS:
                    card_id = "0x%02x%02x%02x%02x" % (uid[0], uid[1], uid[2], uid[3])

                    if card_id in AUTHORIZED:
                        d = get_distance()
                        print(f"✅ Hợp lệ! UID: {card_id} | Khoảng cách: {d}cm")
                        print(f"   Cổng đóng sau {GATE_OPEN_SEC}s (nếu không còn ai)...")
                        led.on()
                        beep_ok()
                        led.off()
                        gate_open()
                        gate_is_open = True
                        gate_open_at = time.ticks_ms()
                    else:
                        print(f"❌ Từ chối! UID: {card_id}")
                        beep_err()

                    last_uid     = uid
                    last_time_ms = now

                reader.halt()

        time.sleep_ms(100)

except KeyboardInterrupt:
    gate_close()
    servo.deinit()
    print("Dừng hệ thống.")