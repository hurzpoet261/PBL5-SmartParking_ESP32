# HUONG DAN CHAY NHANH - SMART PARKING V3

Huong dan nay ap dung cho luong hien tai: MongoDB local, MQTT local, ESP32 RFID
gui MQTT, camera bridge chup anh va backend quyet dinh mo cong.

## 1. Chuan bi dich vu local

### MongoDB

MongoDB chay tai:

```text
mongodb://127.0.0.1:27017
```

Neu cai MongoDB dang ky service Windows:

```powershell
Start-Service MongoDB
```

Neu khong dung service, chay `mongod` theo cach ban da cai dat.

### MQTT broker

Dung Mosquitto local port `1883`.

Kiem tra nhanh:

```powershell
netstat -ano | findstr :1883
```

## 2. Cau hinh backend

```powershell
cd E:\PBL5-SmartParking_ESP32\backend_v3
copy .env.example .env
conda activate pbl5-ai
python check_mongodb.py
python init_data.py
python -m app.main
```

Backend: `http://127.0.0.1:8000`

Trong demo offline nen giu:

```env
API_RELOAD=false
```

## 3. Chay camera bridge

Sua `backend_v3\.env` de tro dung ESP32-CAM:

```env
MQTT_BROKER=127.0.0.1
MQTT_PORT=1883
MQTT_TOPIC_GATE_ACK=pbl5/smartparking/gate_ack
ESP32_CAM_URL=http://IP_ESP32_CAM/capture
BACKEND_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Chay:

```powershell
cd E:\PBL5-SmartParking_ESP32
conda activate pbl5-ai
python backend_v3\camera_bridge.py
```

## 4. Chay frontend

```powershell
cd E:\PBL5-SmartParking_ESP32\frontend_v3
python -m http.server 5500
```

Mo:

```text
http://localhost:5500
```

Khong mo theo duong dan co lap lai `frontend_v3/frontend_v3/...`.

## 5. Upload firmware ESP32 RFID/barrier

Upload cac file sau len ESP32:

- `firmware/main.py` upload voi ten `main.py`
- `firmware/esp32_config.py`
- `firmware/mfrc522.py`
- `firmware/lcd_i2c.py`

Trong `firmware/esp32_config.py`, dung MQTT local:

```python
MQTT_BROKER = "IP_MAY_TINH_CHAY_MOSQUITTO"
MQTT_PORT = 1883
MQTT_TOPIC_RFID = "pbl5/smartparking/rfid_scanned"
MQTT_TOPIC_GATE = "pbl5/smartparking/gate"
MQTT_TOPIC_GATE_ACK = "pbl5/smartparking/gate_ack"
```

Khong upload `firmware/legacy_esp32_main.py` cho luong hien tai. File nay la
firmware HTTP cu.

## 6. Luong van hanh chinh

```text
Quet RFID
-> ESP32 publish MQTT UID
-> camera_bridge.py nhan UID
-> ESP32-CAM chup 2-3 frame
-> Backend OCR + validate RFID/bien so
-> Luu parking_events/sessions
-> Backend publish MQTT open gate
-> ESP32 mo barrier
-> ESP32 publish gate_ack de backend/UI xac nhan
```

`gate_ack` hien tai xac nhan ESP32 da nhan lenh va da chay ham mo servo. Neu
muon xac nhan vat ly tuyet doi barrier da len het hanh trinh, can gan them
cam bien hanh trinh/limit switch va gui ACK sau khi cam bien bao mo.

Endpoint that su xu ly vao/ra:

```text
POST /api/v1/access-events/rfid-camera
```

Endpoint cu:

```text
POST /api/v1/rfid/scan
```

chi con dung cho dang ky/test. Endpoint nay khong tao session, khong tinh phi,
khong mo cong.

## 7. Dang ky the tren web

1. Mo `http://localhost:5500/pages/register-card.html`.
2. Bam `Quet the`.
3. Quet the tren ESP32.
4. UID se hien tren form qua `/api/v1/rfid/latest-scan`.
5. Nhap thong tin khach va xe.
6. Chon:
   - `Theo luot`: khong tao package, tinh phi khi xe ra.
   - `Theo ngay`/`Theo thang`: tao package cho dung xe vua dang ky.
7. Bam `Dang ky`.

Backend se validate:

- Customer phai active.
- Vehicle phai active va thuoc dung customer.
- Moi vehicle chi co mot RFID card active.
- Package ngay/thang chi duoc tao khi vehicle chua co package active con han.

## 8. Kiem tra nhanh

Backend:

```powershell
curl http://127.0.0.1:8000/health
```

Registration/test endpoint:

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/rfid/scan `
  -H "Content-Type: application/json" `
  -d "{\"card_uid\":\"0xa3d6ce05\"}"
```

Ket qua dung la `success: false` va `open_gate: false`, vi endpoint nay khong
duoc phep mo cong.

## 9. Loi thuong gap

- LCD hien MQTT failed/stopped: kiem tra IP broker trong `esp32_config.py`, port
  `1883`, firewall Windows va Mosquitto dang chay.
- Backend ket noi MongoDB loi: kiem tra MongoDB service hoac lenh `mongod`.
- Barrier khong mo du log accepted: kiem tra backend publish MQTT, ESP32 subscribe
  topic gate, topic trong `.env` va `esp32_config.py` phai trung nhau. Trang
  Camera events se hien `Da gui` neu backend da publish va `Barrier mo` khi
  ESP32 da phan hoi `gate_ack`.
- Anh/OCR cham: xem dong `[METRICS]` trong camera bridge de biet cham o capture,
  rank, OCR hay backend.
