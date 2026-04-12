# 🚀 HƯỚNG DẪN CHẠY NHANH - SMART PARKING V3.0

## ⚡ CHẠY NHANH (5 PHÚT)

### Bước 1: Cài MongoDB (Chọn 1 trong 2)

**Cách 1: MongoDB Local (Đơn giản nhất)**
```bash
# Tải MongoDB Community: https://www.mongodb.com/try/download/community
# Cài đặt và chạy (mặc định port 27017)
```

**Cách 2: MongoDB Atlas (Cloud - Miễn phí)**
```bash
# Đăng ký: https://www.mongodb.com/cloud/atlas
# Tạo cluster miễn phí
# Copy connection string
```

### Bước 2: Cấu hình Backend

**Chọn MongoDB:**

**Cách 1: MongoDB Local**
```bash
cd backend_v3
copy .env.local .env
```

**Cách 2: MongoDB Atlas**
```bash
cd backend_v3
copy .env.atlas .env
```

**Kiểm tra kết nối:**
```bash
python check_mongodb.py
```

### Bước 3: Khởi tạo dữ liệu

```bash
python init_data.py
```

Script này sẽ tạo 20 chỗ đỗ xe (A01-A20).

### Bước 4: Chạy Backend

```bash
cd backend_v3
pip install -r requirements.txt
python -m app.main
```

✅ Backend chạy tại: http://localhost:8000

### Bước 5: Chạy Frontend

**Cách 1: Mở trực tiếp**
- Double-click file `frontend_v3/index.html`

**Cách 2: Live Server (Khuyên dùng)**
- Cài extension "Live Server" trong VS Code
- Right-click `index.html` → "Open with Live Server"

✅ Frontend chạy tại: http://localhost:5500

---

## 📱 KIỂM TRA HỆ THỐNG

### 1. Kiểm tra Backend
Mở trình duyệt: http://localhost:8000/docs

Bạn sẽ thấy API documentation (Swagger UI)

### 2. Kiểm tra Frontend
Mở: http://localhost:5500 (hoặc file index.html)

Bạn sẽ thấy Dashboard với:
- 4 thẻ thống kê
- 2 biểu đồ
- Bảng xe đang đỗ

### 3. Test API đầu tiên

**Kiểm tra map chỗ đỗ:**
```bash
curl http://localhost:8000/api/v1/slots/map
```

Bạn sẽ thấy 20 chỗ đỗ đã được tạo từ `init_data.py`.

---

## 🎯 SỬ DỤNG HỆ THỐNG

### 1. Đăng ký thẻ mới

1. Vào trang "Đăng ký thẻ"
2. Điền thông tin:
   - Họ tên: Nguyễn Văn A
   - SĐT: 0123456789
   - Biển số: 29A-12345
   - Loại xe: Xe máy
   - UID thẻ: 0xa3d6ce05
3. Chọn gói cước: Theo lượt
4. Nhấn "Đăng ký"

### 2. Quét thẻ RFID (Giả lập)

**Test check-in:**
```bash
curl -X POST http://localhost:8000/api/v1/rfid/scan \
  -H "Content-Type: application/json" \
  -d '{"card_uid": "0xa3d6ce05"}'
```

**Kết quả:**
```json
{
  "success": true,
  "action": "check_in",
  "message": "Chào mừng! Vui lòng vào.",
  "slot_number": "A01",
  "customer_name": "Nguyễn Văn A"
}
```

**Test check-out:**
```bash
# Quét lại thẻ sau vài phút
curl -X POST http://localhost:8000/api/v1/rfid/scan \
  -H "Content-Type: application/json" \
  -d '{"card_uid": "0xa3d6ce05"}'
```

**Kết quả:**
```json
{
  "success": true,
  "action": "check_out",
  "message": "Tạm biệt! Phí đỗ xe: 5,000đ",
  "fee": 5000,
  "duration_minutes": 60
}
```

### 3. Xem thống kê

- **Dashboard**: Xem tổng quan
- **Map chỗ đỗ**: Xem chỗ trống/đang đỗ
- **Lịch sử**: Xem tất cả phiên ra vào
- **Doanh thu**: Xem biểu đồ doanh thu

---

## 🔧 ESP32 (Tùy chọn)

### Cấu hình WiFi

Sửa file `firmware/esp32_config.py`:
```python
WIFI_SSID = "TenWiFi"
WIFI_PASSWORD = "MatKhauWiFi"
API_URL = "http://192.168.1.100:8000/api/v1/rfid/scan"
```

### Upload lên ESP32

**Dùng Thonny:**
1. Mở Thonny IDE
2. Kết nối ESP32 qua USB
3. Upload tất cả files trong `firmware/`
4. Chạy `esp32_main.py`

**Dùng ampy:**
```bash
pip install adafruit-ampy
ampy --port COM3 put firmware/esp32_config.py
ampy --port COM3 put firmware/esp32_main.py
ampy --port COM3 put firmware/mfrc522.py
ampy --port COM3 put firmware/lcd_i2c.py
```

### Kết nối phần cứng

**RFID RC522:**
- SDA → GPIO 5
- SCK → GPIO 18
- MOSI → GPIO 23
- MISO → GPIO 19
- RST → GPIO 22
- 3.3V → 3.3V
- GND → GND

**LCD I2C:**
- SDA → GPIO 21
- SCL → GPIO 22
- VCC → 5V
- GND → GND

**Servo (Cổng):**
- Signal → GPIO 13
- VCC → 5V
- GND → GND

---

## 🎨 CÁC TRANG GIAO DIỆN

1. **Dashboard** (`/index.html`)
   - Thống kê tổng quan
   - Biểu đồ doanh thu
   - Xe đang đỗ

2. **Đăng ký thẻ** (`/pages/register-card.html`)
   - Form đăng ký đầy đủ
   - Chọn gói cước

3. **Khách hàng** (`/pages/customers.html`)
   - Danh sách khách hàng
   - Tìm kiếm, filter

4. **Xe** (`/pages/vehicles.html`)
   - Danh sách xe
   - Tìm kiếm theo biển số

5. **Map chỗ đỗ** (`/pages/parking-map.html`)
   - Hiển thị grid chỗ đỗ
   - Màu sắc theo trạng thái
   - Real-time update

6. **Gói cước** (`/pages/packages.html`)
   - Danh sách gói cước
   - Filter theo loại

7. **Lịch sử** (`/pages/sessions.html`)
   - Lịch sử ra vào
   - Filter theo ngày

8. **Doanh thu** (`/pages/revenue.html`)
   - Biểu đồ doanh thu
   - Giao dịch gần đây

---

## 🐛 XỬ LÝ LỖI THƯỜNG GẶP

### Lỗi: "Connection refused" khi chạy Backend

**Nguyên nhân:** MongoDB chưa chạy

**Giải pháp:**
```bash
# Windows: Mở Services → Tìm MongoDB → Start
# Linux/Mac: sudo systemctl start mongod
```

### Lỗi: Frontend không kết nối Backend

**Nguyên nhân:** CORS hoặc URL sai

**Giải pháp:**
1. Kiểm tra Backend đã chạy: http://localhost:8000/health
2. Kiểm tra `frontend_v3/assets/js/api.js`:
   ```javascript
   const API_BASE_URL = 'http://localhost:8000/api/v1';
   ```

### Lỗi: "Module not found" khi chạy Backend

**Nguyên nhân:** Chưa cài dependencies

**Giải pháp:**
```bash
cd backend_v3
pip install -r requirements.txt
```

### Lỗi: ESP32 không kết nối WiFi

**Nguyên nhân:** Sai SSID/Password

**Giải pháp:**
1. Kiểm tra `firmware/esp32_config.py`
2. Kiểm tra WiFi 2.4GHz (ESP32 không hỗ trợ 5GHz)

---

## 📊 DỮ LIỆU MẪU

### Tạo dữ liệu test

**1. Khởi tạo 20 chỗ đỗ:**
```bash
curl -X POST http://localhost:8000/api/v1/slots/initialize?total_slots=20
```

**2. Tạo khách hàng mẫu:**
```bash
curl -X POST http://localhost:8000/api/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Nguyễn Văn A",
    "phone": "0123456789",
    "email": "nguyenvana@email.com",
    "customer_type": "walk_in"
  }'
```

**3. Tạo xe mẫu:**
```bash
curl -X POST http://localhost:8000/api/v1/vehicles \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST001",
    "plate_number": "29A-12345",
    "vehicle_type": "motorbike",
    "brand": "Honda",
    "color": "Đỏ"
  }'
```

---

## 🎯 CHECKLIST KHỞI ĐỘNG

- [ ] MongoDB đã cài và chạy
- [ ] File `.env` đã tạo: `copy .env.local .env` hoặc `copy .env.atlas .env`
- [ ] Kiểm tra kết nối: `python check_mongodb.py`
- [ ] Dependencies đã cài: `pip install -r requirements.txt`
- [ ] Khởi tạo dữ liệu: `python init_data.py`
- [ ] Backend chạy thành công: http://localhost:8000/docs
- [ ] Frontend mở được: `index.html`
- [ ] API test thành công: `/health` endpoint
- [ ] Dashboard hiển thị dữ liệu đúng

---

## 📞 TRỢ GIÚP

### Tài liệu chi tiết
- `SETUP_COMPLETE_V3.md` - Hướng dẫn đầy đủ
- `UPGRADE_PLAN.md` - Kế hoạch nâng cấp
- `PROJECT_STATUS.md` - Tình trạng dự án
- `docs/GUIDE.md` - Hướng dẫn sử dụng

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Kiểm tra logs
- Backend: Xem terminal đang chạy `python -m app.main`
- Frontend: Mở DevTools (F12) → Console tab
- ESP32: Mở Serial Monitor trong Thonny

---

## ✅ HOÀN TẤT!

Hệ thống đã sẵn sàng sử dụng! 🎉

**Bước tiếp theo:**
1. Thử đăng ký thẻ mới
2. Test quét thẻ RFID (API hoặc ESP32)
3. Xem thống kê trên Dashboard
4. Khám phá các tính năng khác

**Chúc bạn thành công! 🚀**
