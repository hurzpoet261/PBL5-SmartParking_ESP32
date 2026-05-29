# 📄 CHỨC NĂNG TỪNG FILE TRONG DỰ ÁN

## 📂 BACKEND (Python/FastAPI)

### `backend/app.py` (500+ dòng)
**Vai trò:** Server API chính - Trái tim của hệ thống

**Chức năng:**
- ✅ Xử lý quét thẻ RFID (endpoint quan trọng nhất)
- ✅ Tự động tạo customer/vehicle khi quét thẻ mới
- ✅ Quản lý check-in/check-out
- ✅ Tính phí đỗ xe tự động
- ✅ CRUD operations cho customers, vehicles, sessions
- ✅ Thống kê real-time
- ✅ Lưu trữ dữ liệu vào JSON file

**API Endpoints chính:**
```
POST /api/v1/rfid/scan          → Quét thẻ RFID
GET  /api/v1/customers          → Danh sách khách hàng
GET  /api/v1/vehicles           → Danh sách xe
GET  /api/v1/sessions           → Lịch sử ra vào
GET  /api/v1/stats              → Thống kê
GET  /health                    → Health check
```

**Database Structure:**
```json
{
  "customers": {},      // Khách hàng
  "vehicles": {},       // Xe
  "rfid_cards": {},     // Thẻ RFID
  "sessions": [],       // Lịch sử ra vào
  "stats": {}          // Thống kê
}
```

---

### `backend/config.py`
**Vai trò:** Quản lý cấu hình backend

**Chức năng:**
- ✅ Đường dẫn database file
- ✅ CORS configuration
- ✅ Các settings khác

**Nội dung:**
```python
DB_FILE = "parking_database.json"
CORS_ORIGINS = ["*"]
```

---

### `backend/requirements.txt`
**Vai trò:** Danh sách thư viện Python cần cài đặt

**Nội dung:**
```
fastapi          # Web framework
uvicorn          # ASGI server
pydantic         # Data validation
```

**Cách dùng:**
```bash
pip install -r requirements.txt
```

---

### `backend/.env.example`
**Vai trò:** Template cho environment variables

**Chức năng:**
- ✅ Mẫu cho file .env (nếu cần mở rộng)
- ✅ Hướng dẫn cấu hình môi trường

---

## 📂 FIRMWARE (MicroPython/ESP32)

### `firmware/esp32_config.py`
**Vai trò:** Cấu hình tập trung cho ESP32 - File quan trọng nhất để setup

**Chức năng:**
- ✅ Cấu hình Wi-Fi (SSID, Password)
- ✅ Cấu hình API URL (địa chỉ backend)
- ✅ Cấu hình hardware pins (RFID, Servo, LED, LCD, Ultrasonic)
- ✅ Cấu hình gate (thời gian mở, tự động đóng)
- ✅ Cấu hình messages hiển thị
- ✅ Cấu hình offline mode

**Các cấu hình quan trọng cần sửa:**
```python
# ⚠️ PHẢI SỬA
WIFI_SSID = "Thu Trinh 1"                    # Tên Wi-Fi
WIFI_PASS = "phu760077"                      # Mật khẩu Wi-Fi
API_BASE_URL = "http://192.168.1.233:8000/api/v1"  # IP máy tính

# Hardware Pins (thường không cần sửa)
RFID_SCK_PIN = 18
SERVO_PIN = 14
LED_PIN = 2
...

# Gate Settings
GATE_OPEN_DURATION = 5  # Thời gian mở cổng (giây)
GATE_AUTO_CLOSE = True  # Tự động đóng

# Offline Mode
OFFLINE_MODE_ENABLED = True
OFFLINE_AUTHORIZED_CARDS = ["0xa3d6ce05"]  # Thẻ được phép offline
```

---

### `firmware/esp32_main.py` (600+ dòng)
**Vai trò:** Chương trình chính của ESP32 - Điều khiển toàn bộ hardware

**Chức năng:**

**1. Hardware Initialization:**
- ✅ Khởi tạo RFID Reader (MFRC522)
- ✅ Khởi tạo Servo Motor (điều khiển cổng)
- ✅ Khởi tạo LED & Buzzer
- ✅ Khởi tạo Ultrasonic Sensor (phát hiện người)
- ✅ Khởi tạo LCD Display (hiển thị thông tin)

**2. Hardware Control Functions:**
```python
servo_angle(angle)           # Điều khiển góc servo
gate_open()                  # Mở cổng (0°)
gate_close()                 # Đóng cổng (90°)
get_distance()               # Đo khoảng cách (cm)
is_someone_near()            # Kiểm tra có người gần
beep_success()               # Âm thanh thành công
beep_error()                 # Âm thanh lỗi
display_message(line1, line2) # Hiển thị LCD
```

**3. Wi-Fi Functions:**
```python
connect_wifi()               # Kết nối Wi-Fi với retry
check_wifi_connection()      # Kiểm tra và auto-reconnect
```

**4. API Communication:**
```python
send_rfid_scan(card_uid)     # Gửi dữ liệu lên backend
```

**5. RFID Processing:**
```python
process_rfid_card(card_uid, wifi_connected)
# Xử lý thẻ đã quét:
# - Online: Gửi lên server
# - Offline: Kiểm tra authorized cards
```

**6. Main Loop:**
```python
main()
# Vòng lặp chính:
# - Kết nối Wi-Fi
# - Quét thẻ RFID liên tục
# - Tự động đóng cổng
# - Auto-reconnect Wi-Fi
```

**Luồng hoạt động:**
```
1. Khởi động → Kết nối Wi-Fi → Hiển thị "READY"
2. Loop:
   - Quét thẻ RFID (mỗi 100ms)
   - Gửi lên backend
   - Nhận response
   - Mở cổng nếu thành công
   - Tự động đóng sau 5 giây
   - Kiểm tra Wi-Fi mỗi 30 giây
```

---

### `firmware/mfrc522.py`
**Vai trò:** Driver cho RFID Reader MFRC522

**Chức năng:**
- ✅ Giao tiếp với chip MFRC522 qua SPI
- ✅ Đọc UID thẻ RFID
- ✅ Xử lý protocol ISO 14443A

**Methods chính:**
```python
request(mode)        # Yêu cầu quét thẻ
anticoll()           # Đọc UID thẻ (anti-collision)
halt()               # Dừng giao tiếp
version()            # Đọc version chip
```

**Cách dùng:**
```python
stat, tag = reader.request(reader.REQIDL)
if stat == reader.OK:
    stat, uid = reader.anticoll()
    if stat == reader.OK:
        card_id = "0x%02x%02x%02x%02x" % (uid[0], uid[1], uid[2], uid[3])
```

---

### `firmware/lcd_i2c.py`
**Vai trò:** Driver cho LCD I2C 16x2

**Chức năng:**
- ✅ Giao tiếp với LCD qua I2C
- ✅ Hiển thị text 2 dòng (16 ký tự/dòng)
- ✅ Điều khiển backlight

**Methods chính:**
```python
show_message(line1, line2)   # Hiển thị 2 dòng
clear()                      # Xóa màn hình
backlight_on()               # Bật đèn nền
backlight_off()              # Tắt đèn nền
```

**Cách dùng:**
```python
lcd = LCD_I2C(i2c_addr=0x27, cols=16, rows=2)
lcd.show_message("Hello", "World")
```

---

## 📂 WEB DASHBOARD (HTML/CSS/JavaScript)

### `web/index.html`
**Vai trò:** Giao diện web quản lý - Dashboard chính

**Chức năng:**

**1. Header:**
- ✅ Logo "🚗 Smart Parking"
- ✅ Status badge (Online/Offline)
- ✅ Nút "Làm mới"

**2. Stats Cards (4 thẻ thống kê):**
- ✅ Tổng khách hàng
- ✅ Đang đỗ (active sessions)
- ✅ Tổng lượt quét
- ✅ Tổng xe

**3. Tabs (4 tab):**
- ✅ **Lịch sử ra vào** - Hiển thị sessions với status
- ✅ **Khách hàng** - Danh sách customers
- ✅ **Xe** - Danh sách vehicles với loại xe
- ✅ **Thẻ RFID** - Danh sách cards với status

**4. JavaScript Functions:**
```javascript
refreshAll()         // Làm mới tất cả dữ liệu
loadStats()          // Tải thống kê
loadSessions()       // Tải lịch sử
loadCustomers()      // Tải khách hàng
loadVehicles()       // Tải xe
loadRFIDCards()      // Tải thẻ
switchTab()          // Chuyển tab
setOnlineStatus()    // Cập nhật status badge
```

**5. Auto Refresh:**
```javascript
setInterval(refreshAll, 5000);  // Refresh mỗi 5 giây
```

**6. API Calls:**
```javascript
fetch('http://localhost:8000/api/v1/stats')
fetch('http://localhost:8000/api/v1/sessions')
fetch('http://localhost:8000/api/v1/customers')
...
```

**Thiết kế:**
- ✅ Responsive design
- ✅ Modern UI với gradient background
- ✅ Card-based layout
- ✅ Badge màu cho status
- ✅ Hover effects

---

### `web/app.js`
**Vai trò:** Logic JavaScript (backup/alternative version)

**Chức năng:**
- ✅ Tương tự JavaScript trong index.html
- ✅ Có thêm edit customer/vehicle functions
- ✅ Modal dialogs

**Có thể dùng thay thế hoặc bổ sung cho index.html**

---

### `web/style.css`
**Vai trò:** Styling cho web dashboard

**Chức năng:**
- ✅ CSS variables cho colors
- ✅ Gradient background (purple)
- ✅ Card styles với shadow
- ✅ Table styles
- ✅ Badge styles (success, warning, danger)
- ✅ Button styles
- ✅ Responsive grid
- ✅ Hover effects

**Color Scheme:**
```css
--primary: #3B82F6    (Blue)
--success: #10B981    (Green)
--warning: #F59E0B    (Orange)
--danger: #EF4444     (Red)
--purple: #8B5CF6     (Purple)
```

---

## 📂 SCRIPTS (Batch Files)

### `scripts/start_backend.bat`
**Vai trò:** Khởi động backend server

**Chức năng:**
```batch
1. cd vào thư mục backend
2. Cài đặt dependencies (pip install)
3. Chạy server (python app.py)
4. Pause để xem logs
```

**Cách dùng:**
```bash
# Double-click hoặc
scripts\start_backend.bat
```

**Kết quả:**
- Server chạy tại: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

### `scripts/start_system.bat`
**Vai trò:** Khởi động toàn bộ hệ thống

**Chức năng:**
```batch
1. Mở terminal mới chạy backend
2. Đợi 3 giây (cho backend khởi động)
3. Mở web dashboard trong browser
4. Hiển thị thông báo thành công
```

**Cách dùng:**
```bash
# Double-click hoặc
scripts\start_system.bat
```

**Kết quả:**
- Backend chạy trong terminal riêng
- Web dashboard mở trong browser
- Hệ thống sẵn sàng sử dụng

---

## 📂 DOCS (Documentation)

### `docs/GUIDE.md`
**Vai trò:** Hướng dẫn sử dụng đầy đủ

**Nội dung:**
- ✅ Giới thiệu hệ thống
- ✅ Yêu cầu phần cứng/phần mềm
- ✅ Hướng dẫn cài đặt từng bước
- ✅ Cấu hình Wi-Fi và API
- ✅ Upload firmware lên ESP32
- ✅ Troubleshooting
- ✅ FAQ

---

### `docs/PHAN_TICH_DU_AN.md`
**Vai trò:** Phân tích chi tiết dự án

**Nội dung:**
- ✅ Tổng quan hệ thống
- ✅ Cấu trúc dự án
- ✅ Phân tích từng file
- ✅ Sơ đồ luồng hoạt động
- ✅ Database structure
- ✅ API endpoints
- ✅ Bảo mật & xử lý lỗi

---

### `docs/SO_DO_LUONG.md`
**Vai trò:** Sơ đồ luồng chi tiết

**Nội dung:**
- ✅ Kiến trúc tổng quan
- ✅ Luồng quét thẻ - xe vào
- ✅ Luồng quét thẻ - xe ra
- ✅ Luồng web dashboard
- ✅ Luồng offline mode
- ✅ Luồng tự động đóng cổng
- ✅ Luồng tính phí

---

### `docs/CHUC_NANG_FILE.md` (file này)
**Vai trò:** Tóm tắt chức năng từng file

---

## 📂 ROOT FILES

### `README.md`
**Vai trò:** Tài liệu chính của dự án

**Nội dung:**
- ✅ Giới thiệu ngắn gọn
- ✅ Tính năng chính
- ✅ Cấu trúc dự án
- ✅ Quick start guide
- ✅ Tech stack
- ✅ API endpoints
- ✅ Testing

---

### `.gitignore`
**Vai trò:** Loại trừ files không cần commit

**Nội dung:**
```
__pycache__/
*.pyc
.env
parking_database.json
venv/
```

---

### `CHANGELOG.md`
**Vai trò:** Lịch sử thay đổi dự án

**Nội dung:**
- ✅ Version 2.0.0 - Cleanup & restructure
- ✅ Danh sách files đã xóa
- ✅ Cấu trúc mới
- ✅ Thống kê

---

## 🎯 TÓM TẮT THEO VAI TRÒ

### 🔧 Files cần SỬA khi setup:
1. `firmware/esp32_config.py` - Sửa Wi-Fi SSID, Password, API URL
2. `backend/.env` (nếu có) - Sửa environment variables

### 🚀 Files để CHẠY hệ thống:
1. `scripts/start_backend.bat` - Chạy backend
2. `scripts/start_system.bat` - Chạy toàn bộ
3. `web/index.html` - Mở dashboard

### 📖 Files để ĐỌC hiểu hệ thống:
1. `README.md` - Tổng quan
2. `docs/GUIDE.md` - Hướng dẫn chi tiết
3. `docs/PHAN_TICH_DU_AN.md` - Phân tích kỹ thuật
4. `docs/SO_DO_LUONG.md` - Sơ đồ luồng
5. `docs/CHUC_NANG_FILE.md` - File này

### 💻 Files CORE của hệ thống:
1. `backend/app.py` - Backend API (trái tim)
2. `firmware/esp32_main.py` - ESP32 firmware (não bộ)
3. `web/index.html` - Web dashboard (giao diện)

### 🔌 Files DRIVER/LIBRARY:
1. `firmware/mfrc522.py` - RFID driver
2. `firmware/lcd_i2c.py` - LCD driver

---

**Tài liệu này giúp bạn hiểu rõ chức năng từng file trong dự án!**
