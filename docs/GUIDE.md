# 🚀 HƯỚNG DẪN HOÀN CHỈNH - Smart Parking System v2.0

## 📋 HỆ THỐNG ĐÃ TẠO

### ✅ ESP32 Firmware (Hoàn chỉnh)
- `firmware/esp32_config.py` - Cấu hình tập trung
- `firmware/esp32_main.py` - Firmware chính với logic chặt chẽ
- `firmware/mfrc522.py` - Driver RFID
- `firmware/lcd_i2c.py` - Driver LCD

**Tính năng**:
- ✅ Kết nối Wi-Fi ổn định với retry logic
- ✅ Tự động reconnect khi mất kết nối
- ✅ Gửi dữ liệu lên backend qua HTTP
- ✅ Xử lý offline mode
- ✅ Tự động đóng cổng với phát hiện người
- ✅ Hiển thị LCD đầy đủ
- ✅ Logging chi tiết

### ✅ Backend API (Production-ready)
- `backend/app.py` - API hoàn chỉnh
- `backend/config.py` - Configuration
- `backend/requirements.txt` - Dependencies
- `backend/.env.example` - Environment template

**Tính năng**:
- ✅ RESTful API đầy đủ CRUD
- ✅ Tự động tạo customer/vehicle/card
- ✅ Check-in/check-out logic
- ✅ Tính phí tự động
- ✅ Quản lý capacity
- ✅ Thống kê real-time
- ✅ Error handling tốt
- ✅ Logging chi tiết
- ✅ API documentation (Swagger)

### ✅ Web Dashboard (Đang tạo)
- Giao diện đẹp, hiện đại
- Đầy đủ chức năng quản lý
- Responsive design

---

## 🔧 CẤU HÌNH HỆ THỐNG

### Bước 1: Lấy IP máy tính

```bash
# Windows
ipconfig
# Tìm: IPv4 Address. . . . . . . . . . . : 192.168.1.XXX
```

### Bước 2: Cấu hình ESP32

Sửa `firmware/esp32_config.py`:

```python
# Dòng 10-11
WIFI_SSID = "Ten_WiFi_Cua_Ban"      # ⚠️ THAY ĐỔI
WIFI_PASS = "Mat_Khau_WiFi"         # ⚠️ THAY ĐỔI

# Dòng 18
API_BASE_URL = "http://192.168.1.233:8000/api/v1"  # ⚠️ THAY IP
```

### Bước 3: Cấu hình Backend

```bash
cd backend
copy .env.example .env
# Sửa .env nếu cần
```

---

## 🚀 CHẠY HỆ THỐNG

### A. Chạy Backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Phải thấy:
```
======================================================================
  🚗 SMART PARKING BACKEND API v2.0
======================================================================
  Server:   http://0.0.0.0:8000
  API Docs: http://0.0.0.0:8000/docs
======================================================================
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### B. Upload ESP32 Firmware

**Files cần upload**:
1. `mfrc522.py`
2. `lcd_i2c.py`
3. `esp32_config.py`
4. `esp32_main.py` → đổi tên thành `main.py`

**Sử dụng Thonny IDE**:
1. Mở Thonny
2. Chọn port COM của ESP32
3. Upload từng file
4. Reset ESP32

### C. Mở Web Dashboard

```bash
cd web
# Mở index.html trong trình duyệt
# Hoặc dùng Live Server (VS Code)
```

---

## 🧪 TEST HỆ THỐNG

### Test 1: Backend Health

```bash
curl http://localhost:8000/health
```

Kết quả:
```json
{
  "status": "ok",
  "database": {
    "customers": 0,
    "vehicles": 0,
    "sessions": 0
  }
}
```

### Test 2: Tạo dữ liệu test

```bash
curl -X POST "http://localhost:8000/api/v1/test/scan?card_uid=TEST001"
```

### Test 3: Xem API Docs

Mở trình duyệt:
```
http://localhost:8000/docs
```

### Test 4: ESP32 Serial Monitor

Mở Serial Monitor (115200 baud), phải thấy:
```
==============================================================
  ESP32 SMART PARKING SYSTEM
  Version: 2.0
==============================================================
✅ RFID Reader initialized: 0x92
✅ LCD initialized

📡 Connecting to Wi-Fi: Thu Trinh 1
..........
✅ Wi-Fi connected successfully!
   IP Address: 192.168.1.100

==============================================================
  SYSTEM READY
==============================================================
Waiting for RFID cards...
```

### Test 5: Quét thẻ RFID

Đưa thẻ vào đầu đọc, phải thấy:
```
==============================================================
🔍 RFID Card Detected: 0xa3d6ce05
==============================================================

📤 API Request:
   URL: http://192.168.1.233:8000/api/v1/rfid/scan
   Payload: {'card_uid': '0xa3d6ce05', ...}
📥 API Response:
   Status: 200
   Data: {'success': True, 'action': 'new_registration', ...}

✅ Access Granted!
   Action: new_registration
   Customer: Khách hàng C000001
   Vehicle: XX-0001
   Message: Thẻ mới - Đã tự động đăng ký!

==============================================================
Waiting for next card...
```

---

## 📊 CẤU TRÚC DATABASE

File `backend/parking_database.json`:

```json
{
  "customers": {
    "C000001": {
      "customer_id": "C000001",
      "name": "Khách hàng C000001",
      "phone": null,
      "email": null,
      "address": null,
      "customer_type": "walk_in",
      "created_at": "2026-04-04T...",
      "card_uid": "0xa3d6ce05"
    }
  },
  "vehicles": {
    "V000001": {
      "vehicle_id": "V000001",
      "customer_id": "C000001",
      "plate_number": "XX-0001",
      "vehicle_type": "motorbike",
      "brand": null,
      "model": null,
      "color": null
    }
  },
  "rfid_cards": {
    "0xa3d6ce05": {
      "card_uid": "0xa3d6ce05",
      "customer_id": "C000001",
      "vehicle_id": "V000001",
      "status": "active",
      "card_type": "guest"
    }
  },
  "sessions": [
    {
      "session_id": "S000001",
      "card_uid": "0xa3d6ce05",
      "customer_id": "C000001",
      "vehicle_id": "V000001",
      "entry_gate_id": 1,
      "entry_time": "2026-04-04T...",
      "exit_time": null,
      "status": "in_progress",
      "parking_fee": 0
    }
  ],
  "stats": {
    "total_scans": 1,
    "total_customers": 1,
    "total_vehicles": 1,
    "active_sessions": 1,
    "total_entries": 1,
    "total_exits": 0
  }
}
```

---

## 🎯 QUY TRÌNH HOẠT ĐỘNG

### Lần 1: Quét thẻ mới

```
1. ESP32 quét thẻ RFID → UID: 0xa3d6ce05
2. ESP32 gửi lên Backend
3. Backend kiểm tra → Thẻ chưa có
4. Backend tự động tạo:
   - Customer: C000001
   - Vehicle: V000001
   - RFID Card: 0xa3d6ce05
   - Session: S000001 (in_progress)
5. Backend trả về: success=True, action=new_registration
6. ESP32 nhận → Mở cổng
7. LCD hiển thị: "WELCOME! Khách hàng C000001"
8. Buzzer phát âm thanh thành công
9. Cổng tự động đóng sau 5 giây (nếu không có người)
```

### Lần 2: Quét thẻ đã có (Check-in)

```
1. ESP32 quét thẻ → UID: 0xa3d6ce05
2. Backend kiểm tra → Thẻ đã có, không có session active
3. Backend tạo session mới: S000002 (in_progress)
4. Backend trả về: success=True, action=entry
5. ESP32 mở cổng
6. LCD: "WELCOME! Khách hàng C000001"
```

### Lần 3: Quét thẻ đã có (Check-out)

```
1. ESP32 quét thẻ → UID: 0xa3d6ce05
2. Backend kiểm tra → Thẻ đã có, có session active
3. Backend:
   - Đóng session: status=completed
   - Tính phí (nếu không phải monthly)
   - Cập nhật stats
4. Backend trả về: success=True, action=exit, parking_fee=10000
5. ESP32 mở cổng
6. LCD: "GOODBYE! Fee: 10,000 VNĐ"
```

---

## 📱 API ENDPOINTS

### RFID Scan
```
POST /api/v1/rfid/scan
Body: {
  "card_uid": "0xa3d6ce05",
  "gate_id": 1,
  "distance_cm": 25.0
}
```

### Customers
```
GET    /api/v1/customers          # Danh sách
GET    /api/v1/customers/{id}     # Chi tiết
POST   /api/v1/customers          # Tạo mới
PUT    /api/v1/customers/{id}     # Cập nhật
DELETE /api/v1/customers/{id}     # Xóa
```

### Vehicles
```
GET /api/v1/vehicles              # Danh sách
PUT /api/v1/vehicles/{id}         # Cập nhật
```

### Sessions
```
GET /api/v1/sessions              # Danh sách
GET /api/v1/sessions/{id}         # Chi tiết
```

### Stats
```
GET /api/v1/stats                 # Thống kê tổng quan
GET /api/v1/stats/dashboard       # Thống kê dashboard
```

---

## ✅ CHECKLIST

- [ ] Backend đang chạy (port 8000)
- [ ] Test http://localhost:8000/health OK
- [ ] Lấy IP máy tính
- [ ] Cấu hình Wi-Fi trong esp32_config.py
- [ ] Cấu hình API_BASE_URL trong esp32_config.py
- [ ] Upload firmware lên ESP32
- [ ] ESP32 kết nối Wi-Fi thành công
- [ ] Quét thẻ → Backend tạo database
- [ ] Web Dashboard hiển thị dữ liệu

---

## 🐛 XỬ LÝ LỖI

### Lỗi 1: ESP32 không kết nối Wi-Fi

**Kiểm tra**:
- SSID/password đúng chưa?
- Wi-Fi là 2.4GHz? (ESP32 không hỗ trợ 5GHz)
- Router đang bật?

### Lỗi 2: ESP32 không gửi được request

**Kiểm tra**:
- IP Backend đúng chưa?
- Backend đang chạy?
- Firewall có chặn không?

### Lỗi 3: Web không hiển thị dữ liệu

**Kiểm tra**:
- Backend đang chạy?
- CORS có lỗi không? (F12 → Console)
- API_BASE_URL đúng chưa?

---

**Hệ thống đã sẵn sàng! 🎉**

Đọc file `CONFIG.md` để biết chi tiết cấu hình.
