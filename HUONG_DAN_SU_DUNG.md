# HUONG DAN SU DUNG - SMART PARKING V3

## 1. Khoi dong he thong

Mo 4 terminal rieng:

### MongoDB

```powershell
Start-Service MongoDB
```

### MQTT broker

Chay Mosquitto local port `1883`.

### Backend

```powershell
cd E:\PBL5-SmartParking_ESP32\backend_v3
conda activate pbl5-ai
python -m app.main
```

### Camera bridge

```powershell
cd E:\PBL5-SmartParking_ESP32
conda activate pbl5-ai
python backend_v3\camera_bridge.py
```

### Frontend

```powershell
cd E:\PBL5-SmartParking_ESP32\frontend_v3
python -m http.server 5500
```

Mo `http://localhost:5500`.

## 2. Dang ky the moi

1. Vao `http://localhost:5500/pages/register-card.html`.
2. Bam `Quet the`.
3. Quet the RFID tren ESP32.
4. UID duoc dua vao form tu `/api/v1/rfid/latest-scan`.
5. Nhap thong tin khach hang va xe.
6. Chon goi:
   - `Theo luot`: khong tao package, khi xe ra se tinh phi theo thoi gian.
   - `Theo ngay`: tao package 1 ngay cho xe do.
   - `Theo thang`: tao package 30 ngay cho xe do.
7. Bam `Dang ky`.

Validation khi dang ky:

- The RFID chua duoc dang ky.
- Customer phai ton tai va active.
- Vehicle phai active va thuoc dung customer.
- Mot vehicle chi co mot active RFID card.
- Bien so duoc chuan hoa truoc khi luu de tranh trung lap do dau gach/khoang trang.

## 3. Luong khach da dang ky quet the

```text
RFID da dang ky
-> ESP32 publish MQTT UID
-> camera_bridge chup anh
-> OCR bien so
-> Backend tim card + vehicle
-> So sanh OCR voi bien so du kien
-> Luu event/session
-> Publish MQTT open gate neu accepted
```

Neu chua co session active: he thong tao luot vao.

Neu da co session active: he thong tao luot ra, tinh phi va dong session.

Mien phi khi ra chi ap dung neu chinh xe do co package `daily` hoac `monthly`
active va con han.

## 4. Luong khach vang lai

```text
RFID chua dang ky
-> Bat buoc chup anh va OCR thanh cong
-> Backend tao customer walk_in + vehicle + card tam
-> Tao session vao
-> Mo cong neu luu DB thanh cong
```

Neu OCR khong doc duoc bien so, he thong tu choi de tranh luu luot vao thieu
bien so.

Khi xe ra, the khach vang lai se co session active nen he thong di theo luong ra
va tinh phi theo thoi gian neu khong co package.

## 5. Endpoint quan trong

- `POST /api/v1/access-events/rfid-camera`: luong vao/ra chinh.
- `POST /api/v1/rfid/registration-mode/start`: bat che do quet the de dang ky.
- `GET /api/v1/rfid/latest-scan`: lay UID moi quet cho form dang ky.
- `POST /api/v1/rfid/register-card`: dang ky the.
- `POST /api/v1/rfid/scan`: chi registration/test, khong mo cong.

Khong dung `/api/v1/rfid/scan` de demo luong vao/ra vi endpoint nay khong tao
session va khong cap quyen mo barrier.

## 6. Cau truc firmware

```text
firmware/
  main.py                 # Firmware MQTT hien tai, upload thanh main.py
  esp32_config.py         # WiFi, MQTT, topic, chan GPIO
  mfrc522.py              # RFID RC522
  lcd_i2c.py              # LCD
  legacy_esp32_main.py    # Firmware HTTP cu, khong upload cho luong hien tai
```

## 7. Theo doi trang thai

- Dashboard: tong slot, slot trong, xe dang do.
- Parking map: trang thai tung slot.
- Access events: anh, OCR, decision, review.
- Terminal camera bridge: xem `[METRICS]` de do thoi gian capture/rank/OCR/backend.
- Terminal backend: xem MongoDB, MQTT publisher va access decision.

## 8. Xu ly loi nhanh

- UID khong hien tren form dang ky: dam bao registration mode da bat, ESP32 MQTT
  publish dung topic, camera bridge/backend dang chay.
- Barrier khong mo: kiem tra backend co publish MQTT gate khong, ESP32 co subscribe
  dung `MQTT_TOPIC_GATE` khong.
- OCR fail: kiem tra anh preprocess, goc camera, anh mo, bien so bi cat.
- Package khong tao duoc: xe co the da co package active con han hoac vehicle
  khong thuoc customer dang chon.
