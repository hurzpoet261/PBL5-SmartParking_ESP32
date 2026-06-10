"""
ESP32 Smart Parking - MQTT Gate Firmware

Runtime:
RFID RC522 scan -> publish UID to MQTT topic
MQTT OPEN command -> open servo barrier

Upload this file as main.py when using backend_v3/camera_bridge.py.
"""

from machine import Pin, SPI, PWM
from mfrc522 import MFRC522
import esp32_config as config
import network
import time

try:
    import ujson
except ImportError:
    ujson = None

try:
    from umqtt.simple import MQTTClient
except ImportError:
    MQTTClient = None

try:
    import ubinascii
    import machine
except ImportError:
    ubinascii = None
    machine = None

try:
    from lcd_i2c import LCD_I2C
except ImportError:
    LCD_I2C = None


print("=" * 60)
print("  ESP32 SMART PARKING MQTT GATE")
print("=" * 60)

spi = SPI(
    1,
    baudrate=config.RFID_SPI_BAUDRATE,
    polarity=0,
    phase=0,
    sck=Pin(config.RFID_SCK_PIN),
    mosi=Pin(config.RFID_MOSI_PIN),
    miso=Pin(config.RFID_MISO_PIN),
)
reader = MFRC522(spi, Pin(config.RFID_CS_PIN, Pin.OUT), Pin(config.RFID_RST_PIN, Pin.OUT))

led = Pin(config.LED_PIN, Pin.OUT)
buzzer = Pin(config.BUZZER_PIN, Pin.OUT)
ultrasonic_trig = Pin(config.ULTRASONIC_TRIG_PIN, Pin.OUT)
ultrasonic_echo = Pin(config.ULTRASONIC_ECHO_PIN, Pin.IN)
ENTRY_SERVO_PIN = getattr(config, "SERVO_ENTRY_PIN", getattr(config, "SERVO_PIN", 14))
EXIT_SERVO_PIN = getattr(config, "SERVO_EXIT_PIN", 27)
servo_entry = PWM(Pin(ENTRY_SERVO_PIN), freq=config.SERVO_FREQ)
servo_exit = PWM(Pin(EXIT_SERVO_PIN), freq=config.SERVO_FREQ)

lcd = None
if LCD_I2C:
    try:
        lcd = LCD_I2C(i2c_addr=config.LCD_I2C_ADDR, cols=config.LCD_COLS, rows=config.LCD_ROWS)
    except Exception:
        try:
            lcd = LCD_I2C(i2c_addr=0x3F, cols=config.LCD_COLS, rows=config.LCD_ROWS)
        except Exception:
            lcd = None

client = None
gate_open_state = {"entry": False, "exit": False}
gate_open_at_ms = {"entry": 0, "exit": 0}
last_uid = None
last_scan_ms = 0
last_mqtt_attempt_ms = 0
parking_available = None
parking_total = None
parking_occupied = None
parking_status_at_ms = 0


def log(message):
    if config.DEBUG_MODE:
        print(message)


def display(line1, line2=""):
    log("[LCD] {} | {}".format(line1, line2))
    if lcd:
        try:
            message = line1 or line2 or ""
            lcd.show_message(parking_status_line()[:16], message[:16])
        except Exception:
            pass


def display_slots(message=""):
    display(message or config.MSG_SCAN_CARD)


def parking_status_line():
    if parking_available is None or parking_total is None:
        return "Free: --/--"
    return "Free: {}/{}".format(parking_available, parking_total)


def display_ready():
    display_slots()


def normalize_gate_action(command=None):
    action = ""
    if command:
        try:
            action = str(
                command.get("action")
                or command.get("physical_gate")
                or command.get("gate")
                or command.get("gate_direction")
                or command.get("direction")
                or ""
            ).lower()
        except Exception:
            action = ""
    if action in ("exit", "out", "ra", "gate_out", "cong_ra"):
        return "exit"
    return "entry"


def get_gate_servo(action):
    if action == "exit":
        return servo_exit
    return servo_entry


def get_gate_pin(action):
    if action == "exit":
        return EXIT_SERVO_PIN
    return ENTRY_SERVO_PIN


def get_gate_open_angle(action):
    if action == "exit":
        return getattr(config, "SERVO_EXIT_ANGLE_OPEN", config.SERVO_ANGLE_OPEN)
    return getattr(config, "SERVO_ENTRY_ANGLE_OPEN", config.SERVO_ANGLE_OPEN)


def get_gate_close_angle(action):
    if action == "exit":
        return getattr(config, "SERVO_EXIT_ANGLE_CLOSE", config.SERVO_ANGLE_CLOSE)
    return getattr(config, "SERVO_ENTRY_ANGLE_CLOSE", config.SERVO_ANGLE_CLOSE)


def any_gate_open():
    return gate_open_state.get("entry") or gate_open_state.get("exit")


def servo_angle(servo_obj, angle):
    duty = int(25 + (angle / 180) * 102)
    servo_obj.duty(duty)


def get_distance_cm():
    if not getattr(config, "ULTRASONIC_ENABLED", True):
        return None

    try:
        ultrasonic_trig.value(0)
        time.sleep_us(2)
        ultrasonic_trig.value(1)
        time.sleep_us(10)
        ultrasonic_trig.value(0)

        timeout_us = getattr(config, "ULTRASONIC_TIMEOUT_US", 30_000)
        wait_started = time.ticks_us()
        while ultrasonic_echo.value() == 0:
            if time.ticks_diff(time.ticks_us(), wait_started) > timeout_us:
                return None

        pulse_started = time.ticks_us()
        while ultrasonic_echo.value() == 1:
            if time.ticks_diff(time.ticks_us(), pulse_started) > timeout_us:
                return None

        duration = time.ticks_diff(time.ticks_us(), pulse_started)
        return round((duration * 0.0343) / 2, 1)
    except Exception as exc:
        log("[ULTRASONIC] Read failed: {}".format(exc))
        return None


def is_obstacle_near():
    distance = get_distance_cm()
    if distance is None:
        log("[ULTRASONIC] No valid distance reading")
        return False

    threshold = getattr(config, "ULTRASONIC_THRESHOLD_CM", 10)
    detected = distance < threshold
    log("[ULTRASONIC] distance={}cm threshold={}cm detected={}".format(
        distance,
        threshold,
        detected,
    ))
    return detected


def gate_open(command=None):
    action = normalize_gate_action(command)
    open_angle = get_gate_open_angle(action)
    close_angle = get_gate_close_angle(action)
    log("[GATE] OPEN action={} pin={} open_angle={} close_angle={}".format(
        action,
        get_gate_pin(action),
        open_angle,
        close_angle,
    ))
    servo_angle(get_gate_servo(action), open_angle)
    gate_open_state[action] = True
    gate_open_at_ms[action] = time.ticks_ms()
    led.on()
    display("{} OPEN".format(action.upper()), "MQTT OPEN")
    return action


def gate_close(action="entry", force=False):
    action = normalize_gate_action({"action": action})
    if not force and is_obstacle_near():
        gate_open_at_ms[action] = time.ticks_ms()
        display("{} BLOCKED".format(action.upper()), "Keep open")
        log("[GATE] CLOSE delayed action={} because ultrasonic detects obstacle".format(action))
        return False

    close_angle = get_gate_close_angle(action)
    log("[GATE] CLOSE action={} pin={} close_angle={}".format(action, get_gate_pin(action), close_angle))
    servo_angle(get_gate_servo(action), close_angle)
    gate_open_state[action] = False
    if not any_gate_open():
        led.off()
    display_ready()
    return True


def close_all_gates():
    for action in ("entry", "exit"):
        servo_angle(get_gate_servo(action), get_gate_close_angle(action))
        gate_open_state[action] = False
    led.off()


def beep(freq, duration_ms):
    if freq <= 0:
        return
    half_us = int(500000 // freq)
    cycles = int((duration_ms * 1000) // (half_us * 2))
    for _ in range(cycles):
        buzzer.value(1)
        time.sleep_us(half_us)
        buzzer.value(0)
        time.sleep_us(half_us)


def beep_ok():
    beep(config.BEEP_SUCCESS_FREQ, config.BEEP_SUCCESS_DURATION)


def beep_error():
    beep(config.BEEP_ERROR_FREQ, config.BEEP_ERROR_DURATION)


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return True

    display("WiFi connect", config.WIFI_SSID)
    log("[WIFI] Connecting to {}".format(config.WIFI_SSID))

    try:
        wlan.disconnect()
    except Exception:
        pass

    time.sleep_ms(300)
    wlan.connect(config.WIFI_SSID, config.WIFI_PASS)

    started = time.ticks_ms()
    timeout_ms = config.WIFI_TIMEOUT * 1000
    while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), started) < timeout_ms:
        time.sleep_ms(250)

    if wlan.isconnected():
        log("[WIFI] Connected IP={}".format(wlan.ifconfig()[0]))
        display("WiFi OK", wlan.ifconfig()[0])
        time.sleep_ms(800)
        return True

    log("[WIFI] Failed")
    display("WiFi failed", "check config")
    return False


def wifi_connected():
    wlan = network.WLAN(network.STA_IF)
    return wlan.active() and wlan.isconnected()


def get_client_id():
    if ubinascii and machine:
        try:
            suffix = ubinascii.hexlify(machine.unique_id()).decode()
            return "{}-{}".format(config.MQTT_CLIENT_ID, suffix)
        except Exception:
            pass
    return config.MQTT_CLIENT_ID


def parse_gate_command(payload_text):
    if payload_text.upper() == "OPEN":
        return {"command": "OPEN", "command_id": None}

    if ujson is None:
        log("[GATE] JSON command ignored because ujson is not available")
        return None

    try:
        payload = ujson.loads(payload_text)
    except Exception as exc:
        log("[GATE] Invalid command payload: {}".format(exc))
        return None

    if not isinstance(payload, dict):
        return None

    command = str(payload.get("command", "")).upper()
    if command != "OPEN":
        return None
    return payload


def publish_gate_ack(command, status="opened", error=None, physical_gate=None):
    global client

    if ujson is None or client is None:
        return

    command_id = command.get("command_id") if command else None
    if not command_id:
        return

    payload = {
        "schema": "smartparking.gate_ack.v1",
        "command_id": command_id,
        "command": "OPEN",
        "status": status,
        "device_id": get_client_id(),
        "gate_id": getattr(config, "GATE_ID", 1),
        "action": command.get("action") if command else None,
        "physical_gate": physical_gate or normalize_gate_action(command),
        "event_id": command.get("event_id") if command else None,
        "session_id": command.get("session_id") if command else None,
        "opened_at_ms": time.ticks_ms(),
    }
    if error:
        payload["error"] = str(error)

    try:
        topic = getattr(config, "MQTT_TOPIC_GATE_ACK", "pbl5/smartparking/gate_ack")
        client.publish(topic, ujson.dumps(payload).encode())
        log("[GATE] ACK published command_id={} status={}".format(command_id, status))
    except Exception as exc:
        log("[GATE] ACK publish failed: {}".format(exc))


def on_mqtt_message(topic, payload):
    topic_text = topic.decode() if isinstance(topic, bytes) else str(topic)
    payload_text = payload.decode().strip() if isinstance(payload, bytes) else str(payload).strip()

    log("[MQTT] RX topic={} payload={}".format(topic_text, payload_text))

    if topic_text == config.MQTT_TOPIC_GATE:
        command = parse_gate_command(payload_text)
        if command:
            try:
                opened_gate = gate_open(command)
                beep_ok()
                publish_gate_ack(command, "opened", physical_gate=opened_gate)
            except Exception as exc:
                log("[GATE] OPEN failed: {}".format(exc))
                beep_error()
                publish_gate_ack(command, "failed", exc)
        else:
            log("[GATE] Ignored unsupported command")
    elif topic_text == config.MQTT_TOPIC_PARKING_STATUS:
        update_parking_status(payload_text)


def update_parking_status(payload_text):
    global parking_available, parking_total, parking_occupied, parking_status_at_ms

    if ujson is None:
        log("[PARKING] ujson not available")
        return

    try:
        status = ujson.loads(payload_text)
        available = int(status.get("available", 0))
        total = int(status.get("total", 0))
        occupied = int(status.get("occupied", max(total - available, 0)))
    except Exception as exc:
        log("[PARKING] Invalid status payload: {}".format(exc))
        return

    parking_available = available
    parking_total = total
    parking_occupied = occupied
    parking_status_at_ms = time.ticks_ms()
    log("[PARKING] Free {}/{} occupied={}".format(parking_available, parking_total, parking_occupied))

    display_ready()


def connect_mqtt(force=False):
    global client, last_mqtt_attempt_ms

    if MQTTClient is None:
        log("[MQTT] umqtt.simple not available")
        display("MQTT missing", "umqtt.simple")
        return False

    now = time.ticks_ms()
    if not force and time.ticks_diff(now, last_mqtt_attempt_ms) < config.MQTT_RECONNECT_DELAY * 1000:
        return client is not None

    last_mqtt_attempt_ms = now

    if not wifi_connected() and not connect_wifi():
        return False

    try:
        if client:
            try:
                client.disconnect()
            except Exception:
                pass

        client_id = get_client_id()
        client = MQTTClient(
            client_id=client_id,
            server=config.MQTT_BROKER,
            port=config.MQTT_PORT,
            keepalive=config.MQTT_KEEPALIVE,
        )
        client.set_callback(on_mqtt_message)
        client.connect(clean_session=True)
        client.subscribe(config.MQTT_TOPIC_GATE)
        client.subscribe(config.MQTT_TOPIC_PARKING_STATUS)

        log("[MQTT] Connected broker={}:{}".format(config.MQTT_BROKER, config.MQTT_PORT))
        log("[MQTT] Subscribed {}".format(config.MQTT_TOPIC_GATE))
        log("[MQTT] Subscribed {}".format(config.MQTT_TOPIC_PARKING_STATUS))
        display("MQTT OK", "Ready")
        return True

    except Exception as exc:
        log("[MQTT] Connect failed: {}".format(exc))
        display("MQTT failed", "retrying")
        client = None
        return False


def mqtt_check_messages():
    global client

    if client is None:
        connect_mqtt()
        return

    try:
        client.check_msg()
    except Exception as exc:
        log("[MQTT] check_msg failed: {}".format(exc))
        client = None


def publish_rfid(card_uid):
    global client

    if client is None and not connect_mqtt(force=True):
        beep_error()
        return False

    try:
        client.publish(config.MQTT_TOPIC_RFID, card_uid.encode())
        log("[RFID] Published UID={} topic={}".format(card_uid, config.MQTT_TOPIC_RFID))
        display("RFID sent", card_uid[-8:])
        beep_ok()
        return True

    except Exception as exc:
        log("[MQTT] Publish failed: {}".format(exc))
        client = None
        beep_error()
        display("Publish fail", "retry later")
        return False


def read_rfid_uid():
    stat, _tag = reader.request(reader.REQIDL)
    if stat != reader.OK:
        return None

    stat, uid = reader.anticoll()
    if stat != reader.OK or uid is None or len(uid) < 4:
        return None

    try:
        reader.halt()
    except Exception:
        pass

    return "0x%02x%02x%02x%02x" % (uid[0], uid[1], uid[2], uid[3])


def handle_gate_auto_close():
    if not config.GATE_AUTO_CLOSE:
        return

    now = time.ticks_ms()
    for action in ("entry", "exit"):
        if not gate_open_state.get(action):
            continue
        elapsed = time.ticks_diff(now, gate_open_at_ms.get(action, 0))
        if elapsed >= config.GATE_OPEN_DURATION * 1000:
            gate_close(action)


def main():
    global last_uid, last_scan_ms, client

    close_all_gates()
    connect_wifi()
    connect_mqtt(force=True)
    display_ready()

    log("[SYSTEM] Ready. Scan RFID card.")

    while True:
        if not wifi_connected():
            log("[WIFI] Disconnected")
            connect_wifi()
            client = None

        mqtt_check_messages()
        handle_gate_auto_close()

        uid = read_rfid_uid()
        if uid:
            now = time.ticks_ms()
            duplicate = uid == last_uid and time.ticks_diff(now, last_scan_ms) < config.SCAN_COOLDOWN_MS
            if not duplicate:
                log("[RFID] UID detected: {}".format(uid))
                publish_rfid(uid)
                last_uid = uid
                last_scan_ms = now

        time.sleep_ms(80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        close_all_gates()
        servo_entry.deinit()
        servo_exit.deinit()
        display("Stopped", "")
        print("Stopped")
