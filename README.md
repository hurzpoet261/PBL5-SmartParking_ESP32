# Smart Parking System V3

He thong bai do xe thong minh dung ESP32, RFID, ESP32-CAM, FastAPI, MongoDB,
MQTT va web dashboard.

## Luong van hanh hien tai

Luong mo cong chinh da duoc khoa theo camera/OCR:

```text
ESP32 RFID -> MQTT -> camera_bridge.py -> ESP32-CAM chup anh
           -> Backend POST /api/v1/access-events/rfid-camera
           -> OCR + validate RFID/bien so + luu DB
           -> Backend publish MQTT open gate
           -> ESP32 nhan lenh va mo barrier
           -> ESP32 publish gate_ack, frontend hien ACK barrier
```

`POST /api/v1/rfid/scan` chi con dung cho dang ky the/test. Endpoint nay khong
tao session, khong tinh phi, khong cap quyen mo cong.

## Firmware

Dung firmware chinh:

- `firmware/main.py`
- `firmware/esp32_config.py`
- `firmware/mfrc522.py`
- `firmware/lcd_i2c.py`

Upload `firmware/main.py` len ESP32 voi ten `main.py`.

`firmware/legacy_esp32_main.py` la firmware HTTP cu, chi giu lai de tham khao.
Khong upload file nay cho luong camera/OCR hien tai.

## Backend

```powershell
cd E:\PBL5-SmartParking_ESP32\backend_v3
copy .env.example .env
conda activate pbl5-ai
python -m app.main
```

Backend mac dinh chay tai `http://127.0.0.1:8000`.
Demo offline nen de `API_RELOAD=false` trong `backend_v3\.env`.

## Camera Bridge

```powershell
cd E:\PBL5-SmartParking_ESP32
conda activate pbl5-ai
python backend_v3\camera_bridge.py
```

Camera bridge nhan UID tu MQTT, chup anh tu ESP32-CAM, goi OCR/Backend va ghi
metrics thoi gian xu ly.

Trong `backend_v3\.env`, sua `ESP32_CAM_URL=http://IP_ESP32_CAM/capture` dung
IP ESP32-CAM cua mang LAN demo.

## Frontend

```powershell
cd E:\PBL5-SmartParking_ESP32\frontend_v3
python -m http.server 5500
```

Mo `http://localhost:5500`.

## Package va phi

- `per_use`: khong tao package trong DB, phi tinh theo tung session khi xe ra.
- `daily`, `monthly`: tao package theo dung xe cua dung khach.
- Khi xe ra, mien phi chi ap dung neu xe do co package `daily/monthly` active va
  con han.

## Endpoint chinh

- `POST /api/v1/access-events/rfid-camera`: luong vao/ra that te.
- `POST /api/v1/rfid/registration-mode/start`: bat che do dang ky the.
- `GET /api/v1/rfid/latest-scan`: lay UID moi quet de dien form dang ky.
- `POST /api/v1/rfid/register-card`: dang ky the sau khi validate customer-vehicle-card.
- `POST /api/v1/rfid/scan`: registration/test only, khong mo cong.

API docs: `http://127.0.0.1:8000/docs`.

## MQTT topics local

- RFID scan: `pbl5/smartparking/rfid_scanned`
- Gate command: `pbl5/smartparking/gate`
- Gate ACK: `pbl5/smartparking/gate_ack`
- Parking status LCD: `pbl5/smartparking/parking_status`

Gate ACK hien tai la xac nhan ESP32 da nhan lenh va chay servo mo cong. Neu can
xac nhan vat ly barrier da mo het hanh trinh, can bo sung cam bien hanh trinh.
