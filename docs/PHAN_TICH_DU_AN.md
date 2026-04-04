# 📚 PHÂN TÍCH DỰ ÁN SMART PARKING

## 🎯 TỔNG QUAN HỆ THỐNG

Hệ thống Smart Parking là một giải pháp quản lý bãi đỗ xe thông minh sử dụng công nghệ RFID, kết hợp 3 thành phần chính:

1. **ESP32 Firmware** - Phần cứng điều khiển cổng và quét thẻ
2. **Backend API** - Server xử lý logic và lưu trữ dữ liệu
3. **Web Dashboard** - Giao diện quản lý và giám sát

---

## 📁 CẤU TRÚC DỰ ÁN

```
PBL5-SmartParking_ESP32/
├── backend/              # Backend API Server
│   ├── app.py           # Main API application
│   ├── config.py        # Configuration management
│   ├── requirements.txt # Python dependencies
│   └── .env.example     # Environment variables template
│
├── firmware/            # ESP32 Firmware (MicroPython)
│   ├── esp32_config.py # Cấu hình ESP32
│   ├── esp32_main.py   # Chương trình chính
│   ├── mfrc522.py      # Driver RFID
│   └── lcd_i2c.py      # Driver LCD
│
├── web/                 # Web Dashboard
│   ├── index.html      # Giao diện chính
│   ├── app.js          # Logic JavaScript
│   └── style.css       # Styling
│
├── docs/                # Documentation
│   └── GUIDE.md        # Hướng dẫn sử dụng
│
├── scripts/             # Utility Scripts
│   ├── start_backend.bat   # Khởi động backend
│   └── start_system.bat    # Khởi động toàn bộ
│
└── README.md            # Tài liệu chính
```

---

## 🔧 PHÂN TÍCH CHI TIẾT TỪNG FILE

### 📂 BACKEND (Python/FastAPI)

#### 1. `backend/app.py` (500+ dòng)
**Chức năng:** Server API chính xử lý toàn bộ logic nghiệp vụ

**Các thành phần chính:**

**A. Models & Enums:**
```python
- VehicleType: motorbike, car, bicycle
- CardStatus: active, inactive, lost, expired
- SessionStatus: in_progress, completed, cancelled
- CustomerType: walk_in, monthly, vip
```

**B. Database Functions:**
- `init_db()` - Khởi tạo database JSON mới
- `load_db()` - Đọc dữ liệu từ file
- `save_db()` - Lưu dữ liệu vào file
- `generate_id()` - Tạo ID tự động (C000001, V000001, S000001)

**C. API Endpoints:**

**1. Health & Info:**
- `GET /` - Thông tin API
- `GET /health` - Kiểm tra trạng thái server

**2. RFID Scan (Endpoint quan trọng nhất):**
- `POST /api/v1/rfid/scan` - Xử lý quét thẻ RFID

**Logic hoạt động:**
```
1. Nhận card_uid từ ESP32
2. Kiểm tra thẻ đã tồn tại?
   
   A. THẺ CŨ:
      - Kiểm tra trạng thái thẻ (active/inactive)
      - Tìm session đang mở (in_progress)
      
      a. Có session đang mở → CHECK-OUT (xe ra)
         - Đóng session
         - Tính phí đỗ xe (nếu không phải monthly)
         - Cập nhật thống kê
         - Trả về: exit, parking_fee, duration
      
      b. Không có session → CHECK-IN (xe vào)
         - Kiểm tra capacity (bãi đầy?)
         - Tạo session mới
         - Cập nhật thống kê
         - Trả về: entry, customer_name, vehicle_plate
   
   B. THẺ MỚI (Tự động đăng ký):
      - Tạo customer mới (C000001)
      - Tạo vehicle mới (V000001)
      - Tạo RFID card mới
      - Tạo session đầu tiên
      - Trả về: new_registration, customer_id, vehicle_id
```

**3. Customer Management:**
- `GET /api/v1/customers` - Danh sách khách hàng (có pagination)
- `GET /api/v1/customers/{id}` - Chi tiết 1 khách hàng
- `POST /api/v1/customers` - Tạo khách hàng mới
- `PUT /api/v1/customers/{id}` - Cập nhật thông tin
- `DELETE /api/v1/customers/{id}` - Xóa khách hàng

**4. Vehicle Management:**
- `GET /api/v1/vehicles` - Danh sách xe
- `PUT /api/v1/vehicles/{id}` - Cập nhật thông tin xe

**5. Session Management:**
- `GET /api/v1/sessions` - Lịch sử ra vào
- `GET /api/v1/sessions/{id}` - Chi tiết 1 phiên

**6. RFID Cards:**
- `GET /api/v1/rfid-cards` - Danh sách thẻ RFID

**7. Statistics:**
- `GET /api/v1/stats` - Thống kê tổng quan
- `GET /api/v1/stats/dashboard` - Thống kê cho dashboard

**8. Testing:**
- `POST /api/v1/test/scan` - Test quét thẻ
- `DELETE /api/v1/test/reset` - Reset database

**D. Database Structure:**
```json
{
  "customers": {
    "C000001": {
      "customer_id": "C000001",
      "name": "Khách hàng C000001",
      "phone": null,
      "email": null,
      "customer_type": "walk_in",
      "created_at": "2026-04-04T10:00:00"
    }
  },
  "vehicles": {
    "V000001": {
      "vehicle_id": "V000001",
      "customer_id": "C000001",
      "plate_number": "XX-0001",
      "vehicle_type": "motorbike"
    }
  },
  "rfid_cards": {
    "0xa3d6ce05": {
      "card_uid": "0xa3d6ce05",
      "customer_id": "C000001",
      "vehicle_id": "V000001",
      "status": "active"
    }
  },
  "sessions": [
    {
      "session_id": "S000001",
      "card_uid": "0xa3d6ce05",
      "entry_time": "2026-04-04T10:00:00",
      "exit_time": null,
      "status": "in_progress",
      "parking_fee": 0
    }
  ],
  "stats": {
    "total_customers": 1,
    "total_vehicles": 1,
    "active_sessions": 1,
    "total_scans": 5
  }
}
```

#### 2. `backend/config.py`
**Chức năng:** Quản lý cấu hình backend

```python
DB_FILE = "parking_database.json"
CORS_ORIGINS = ["*"]  # Cho phép mọi origin
```

#### 3. `backend/requirements.txt`
**Chức năng:** Danh sách thư viện Python cần cài đặt

```
fastapi - Web framework
uvicorn - ASGI server
pydantic - Data validation
```

#### 4. `backend/.env.example`
**Chức năng:** Template cho biến môi trường (nếu cần mở rộng)

---

### 📂 FIRMWARE (MicroPython/ESP32)

#### 1. `firmware/esp32_config.py`
**Chức năng:** Cấu hình tập trung cho ESP32

**Các cấu hình chính:**

**A. Wi-Fi:**
```python
WIFI_SSID = "Thu Trinh 1"
WIFI_PASS = "phu760077"
WIFI_TIMEOUT = 20  # giây
```

**B. API:**
```python
API_BASE_URL = "http://192.168.1.233:8000/api/v1"
API_TIMEOUT = 10  # giây
```

**C. Gate:**
```python
GATE_ID = 1
GATE_NAME = "Cổng chính"
GATE_OPEN_DURATION = 5  # giây
GATE_AUTO_CLOSE = True
```

**D. Hardware Pins:**
```python
# RFID (SPI)
RFID_SCK_PIN = 18
RFID_MOSI_PIN = 23
RFID_MISO_PIN = 19
RFID_CS_PIN = 5
RFID_RST_PIN = 4

# Servo
SERVO_PIN = 14
SERVO_ANGLE_OPEN = 0
SERVO_ANGLE_CLOSE = 90

# LED & Buzzer
LED_PIN = 2
BUZZER_PIN = 13

# Ultrasonic
ULTRASONIC_TRIG_PIN = 26
ULTRASONIC_ECHO_PIN = 35
ULTRASONIC_THRESHOLD_CM = 30

# LCD I2C
LCD_I2C_ADDR = 0x27
LCD_SDA_PIN = 21
LCD_SCL_PIN = 22
```

**E. Messages:**
```python
MSG_WELCOME = ">>> READY <<<"
MSG_SCAN_CARD = "Scan RFID Card"
MSG_ACCEPTED = "WELCOME!"
MSG_DENIED = "ACCESS DENIED"
```

**F. Offline Mode:**
```python
OFFLINE_MODE_ENABLED = True
OFFLINE_ALLOW_ALL_CARDS = False
OFFLINE_AUTHORIZED_CARDS = ["0xa3d6ce05", "0xcc40d906"]
```

#### 2. `firmware/esp32_main.py` (600+ dòng)
**Chức năng:** Chương trình chính của ESP32

**Các thành phần:**

**A. Hardware Initialization:**
```python
- RFID Reader (MFRC522) qua SPI
- Servo Motor (PWM)
- LED & Buzzer
- Ultrasonic Sensor (HC-SR04)
- LCD Display (I2C)
```

**B. Hardware Control Functions:**

1. `servo_angle(angle)` - Điều khiển góc servo
2. `gate_open()` - Mở cổng (servo 0°)
3. `gate_close()` - Đóng cổng (servo 90°)
4. `get_distance()` - Đo khoảng cách (cm)
5. `is_someone_near()` - Kiểm tra có người gần
6. `beep(freq, duration)` - Phát âm thanh
7. `beep_success()` - Âm thanh thành công
8. `beep_error()` - Âm thanh lỗi
9. `display_message(line1, line2)` - Hiển thị LCD

**C. Wi-Fi Functions:**

1. `connect_wifi()` - Kết nối Wi-Fi với retry logic
   ```python
   - Kết nối đến WIFI_SSID
   - Timeout 20 giây
   - Hiển thị IP address
   - Hiển thị signal strength
   ```

2. `check_wifi_connection()` - Kiểm tra và tự động kết nối lại
   ```python
   - Gọi mỗi 30 giây
   - Tự động reconnect nếu mất kết nối
   ```

**D. API Communication:**

`send_rfid_scan(card_uid)` - Gửi dữ liệu lên backend
```python
Payload:
{
  "card_uid": "0xa3d6ce05",
  "gate_id": 1,
  "distance_cm": 25.0,
  "timestamp": 1234567890
}

Response:
{
  "success": true,
  "action": "entry" | "exit" | "new_registration",
  "message": "Chào mừng!",
  "customer_name": "Nguyễn Văn A",
  "vehicle_plate": "59A1-12345"
}
```

**E. RFID Processing:**

`process_rfid_card(card_uid, wifi_connected)` - Xử lý thẻ đã quét
```python
Logic:
1. Bật LED
2. Hiển thị "SCANNING..." trên LCD
3. Nếu online:
   - Gửi lên server
   - Nếu success → Mở cổng, beep success
   - Nếu denied → Beep error
4. Nếu offline:
   - Kiểm tra trong OFFLINE_AUTHORIZED_CARDS
   - Nếu có → Mở cổng
   - Nếu không → Từ chối
5. Tắt LED
```

**F. Main Loop:**

`main()` - Vòng lặp chính
```python
1. Khởi tạo:
   - Đóng cổng
   - Kết nối Wi-Fi
   - Hiển thị "READY"

2. Loop (mỗi 100ms):
   - Kiểm tra Wi-Fi (mỗi 30s)
   
   - Tự động đóng cổng:
     * Nếu cổng mở > 5 giây
     * Kiểm tra có người gần không
     * Nếu không có → Đóng cổng
   
   - Quét thẻ RFID:
     * Đọc card UID
     * Kiểm tra cooldown (3 giây)
     * Xử lý thẻ
     * Nếu thành công → Mở cổng
```

#### 3. `firmware/mfrc522.py`
**Chức năng:** Driver cho RFID Reader MFRC522

**Các method chính:**
- `request()` - Yêu cầu quét thẻ
- `anticoll()` - Đọc UID thẻ
- `halt()` - Dừng giao tiếp với thẻ
- `version()` - Đọc phiên bản chip

#### 4. `firmware/lcd_i2c.py`
**Chức năng:** Driver cho LCD I2C 16x2

**Các method chính:**
- `show_message(line1, line2)` - Hiển thị 2 dòng text
- `clear()` - Xóa màn hình
- `backlight_on()` / `backlight_off()` - Điều khiển đèn nền

---

### 📂 WEB DASHBOARD (HTML/CSS/JavaScript)

#### 1. `web/index.html`
**Chức năng:** Giao diện web quản lý

**Cấu trúc:**

**A. Header:**
- Logo "🚗 Smart Parking"
- Status badge (Online/Offline)
- Nút "Làm mới"

**B. Stats Cards (4 thẻ):**
- Tổng khách hàng
- Đang đỗ (active sessions)
- Tổng lượt quét
- Tổng xe

**C. Tabs (4 tab):**
1. **Lịch sử ra vào** - Hiển thị sessions
2. **Khách hàng** - Danh sách customers
3. **Xe** - Danh sách vehicles
4. **Thẻ RFID** - Danh sách cards

**D. Tables:**
- Hiển thị dữ liệu dạng bảng
- Có badge màu cho status
- Responsive design

**E. JavaScript Functions:**
```javascript
- refreshAll() - Làm mới tất cả dữ liệu
- loadStats() - Tải thống kê
- loadSessions() - Tải lịch sử
- loadCustomers() - Tải khách hàng
- loadVehicles() - Tải xe
- loadRFIDCards() - Tải thẻ
- switchTab() - Chuyển tab
- formatDate() - Format ngày tháng
```

**F. Auto Refresh:**
```javascript
setInterval(refreshAll, 5000);  // Refresh mỗi 5 giây
```

#### 2. `web/app.js`
**Chức năng:** Logic JavaScript (backup/alternative)

Tương tự như JavaScript trong index.html, có thêm:
- Edit customer
- Edit vehicle
- Modal dialogs

#### 3. `web/style.css`
**Chức năng:** Styling cho web dashboard

**Thiết kế:**
- Gradient background (purple)
- Card-based layout
- Modern UI với border-radius
- Responsive grid
- Hover effects
- Badge colors (success, warning, danger)

---

### 📂 SCRIPTS (Batch Files)

#### 1. `scripts/start_backend.bat`
**Chức năng:** Khởi động backend server

```batch
1. cd vào thư mục backend
2. pip install -q -r requirements.txt
3. python app.py
4. pause
```

#### 2. `scripts/start_system.bat`
**Chức năng:** Khởi động toàn bộ hệ thống

```batch
1. Mở terminal mới chạy backend
2. Đợi 3 giây
3. Mở web dashboard trong browser
4. Hiển thị thông báo thành công
```

---

## 🔄 SƠ ĐỒ LUỒNG HOẠT ĐỘNG

### 1. LUỒNG CHÍNH - QUÉT THẺ RFID

```
┌─────────────┐
│   ESP32     │
│  (Firmware) │
└──────┬──────┘
       │
       │ 1. Quét thẻ RFID
       │    card_uid = "0xa3d6ce05"
       │
       ▼
┌─────────────────────┐
│ process_rfid_card() │
└──────┬──────────────┘
       │
       │ 2. Gửi HTTP POST
       │    /api/v1/rfid/scan
       │    {card_uid, gate_id, distance_cm}
       │
       ▼
┌─────────────┐
│   Backend   │
│   (API)     │
└──────┬──────┘
       │
       │ 3. Xử lý logic
       │
       ├─── THẺ MỚI ────────────────┐
       │                             │
       │ 4a. Tạo customer mới        │
       │ 4b. Tạo vehicle mới         │
       │ 4c. Tạo RFID card           │
       │ 4d. Tạo session (CHECK-IN)  │
       │                             │
       └─────────────────────────────┤
       │                             │
       ├─── THẺ CŨ - Chưa có session ┤
       │                             │
       │ 5a. Tạo session (CHECK-IN)  │
       │ 5b. Cập nhật stats          │
       │                             │
       └─────────────────────────────┤
       │                             │
       ├─── THẺ CŨ - Có session ─────┤
       │                             │
       │ 6a. Đóng session (CHECK-OUT)│
       │ 6b. Tính phí đỗ xe          │
       │ 6c. Cập nhật stats          │
       │                             │
       └─────────────────────────────┘
       │
       │ 7. Trả về response
       │    {success, action, message}
       │
       ▼
┌─────────────┐
│   ESP32     │
└──────┬──────┘
       │
       │ 8. Xử lý response
       │
       ├─── Success ────────────┐
       │                        │
       │ 9a. Mở cổng (servo 0°) │
       │ 9b. Beep success       │
       │ 9c. Hiển thị "WELCOME" │
       │                        │
       └────────────────────────┤
       │                        │
       ├─── Denied ─────────────┤
       │                        │
       │ 10a. Beep error        │
       │ 10b. Hiển thị "DENIED" │
       │                        │
       └────────────────────────┘
       │
       │ 11. Đợi 5 giây
       │
       ▼
┌─────────────────────┐
│ Tự động đóng cổng   │
│ (nếu không có người)│
└─────────────────────┘
```

### 2. LUỒNG PHỤ - WEB DASHBOARD

```
┌─────────────┐
│   Browser   │
│ (Dashboard) │
└──────┬──────┘
       │
       │ 1. Mở web/index.html
       │
       ▼
┌─────────────────┐
│ Auto refresh    │
│ (mỗi 5 giây)    │
└──────┬──────────┘
       │
       │ 2. Gọi API
       │
       ├─── GET /api/v1/stats ──────────┐
       │                                 │
       │ 3a. Tổng khách hàng             │
       │ 3b. Đang đỗ                     │
       │ 3c. Tổng lượt quét              │
       │                                 │
       └─────────────────────────────────┤
       │                                 │
       ├─── GET /api/v1/sessions ────────┤
       │                                 │
       │ 4. Lịch sử ra vào (50 records)  │
       │                                 │
       └─────────────────────────────────┤
       │                                 │
       ├─── GET /api/v1/customers ───────┤
       │                                 │
       │ 5. Danh sách khách hàng         │
       │                                 │
       └─────────────────────────────────┤
       │                                 │
       ├─── GET /api/v1/vehicles ────────┤
       │                                 │
       │ 6. Danh sách xe                 │
       │                                 │
       └─────────────────────────────────┤
       │                                 │
       ├─── GET /api/v1/rfid-cards ──────┤
       │                                 │
       │ 7. Danh sách thẻ RFID           │
       │                                 │
       └─────────────────────────────────┘
       │
       │ 8. Cập nhật UI
       │    - Stats cards
       │    - Tables
       │    - Status badge
       │
       ▼
┌─────────────────┐
│ Hiển thị dữ liệu│
└─────────────────┘
```

### 3. LUỒNG TỰ ĐỘNG ĐÓNG CỔNG

```
┌─────────────┐
│ Cổng đang mở│
└──────┬──────┘
       │
       │ 1. Đợi 5 giây
       │
       ▼
┌──────────────────────┐
│ Kiểm tra ultrasonic  │
│ get_distance()       │
└──────┬───────────────┘
       │
       ├─── Khoảng cách < 30cm ───┐
       │                           │
       │ 2a. Có người gần          │
       │ 2b. Giữ cổng mở           │
       │ 2c. Reset timer           │
       │                           │
       └───────────────────────────┤
       │                           │
       ├─── Khoảng cách >= 30cm ───┤
       │                           │
       │ 3a. Không có người        │
       │ 3b. Đóng cổng (servo 90°) │
       │ 3c. Hiển thị "READY"      │
       │                           │
       └───────────────────────────┘
```

---

## 🔐 BẢO MẬT & XỬ LÝ LỖI

### 1. Backend
- CORS enabled (cho phép mọi origin)
- Validation với Pydantic models
- Try-catch cho database operations
- Logging chi tiết

### 2. ESP32
- Wi-Fi auto-reconnect
- Offline mode với authorized cards
- API timeout (10 giây)
- Cooldown giữa các lần quét (3 giây)

### 3. Web Dashboard
- Error handling cho API calls
- Online/Offline status indicator
- Auto-retry khi mất kết nối

---

## 📊 DỮ LIỆU & THỐNG KÊ

### Database (JSON File)
- **Customers**: Thông tin khách hàng
- **Vehicles**: Thông tin xe
- **RFID Cards**: Thẻ RFID và liên kết
- **Sessions**: Lịch sử ra vào
- **Stats**: Thống kê real-time

### Thống kê được theo dõi:
- Tổng khách hàng
- Tổng xe
- Tổng lượt quét
- Đang đỗ (active sessions)
- Tổng lượt vào/ra
- Doanh thu hôm nay

---

## 🚀 QUY TRÌNH HOẠT ĐỘNG HOÀN CHỈNH

### Bước 1: Khởi động hệ thống
```
1. Chạy backend: scripts\start_backend.bat
   → Server chạy tại http://localhost:8000
   → Tạo parking_database.json nếu chưa có

2. Upload firmware lên ESP32
   → Kết nối Wi-Fi
   → Kết nối đến backend API
   → Hiển thị "READY" trên LCD

3. Mở web dashboard: web\index.html
   → Kết nối đến backend
   → Hiển thị stats và dữ liệu
   → Auto refresh mỗi 5 giây
```

### Bước 2: Xe vào (CHECK-IN)
```
1. Khách hàng quét thẻ RFID
2. ESP32 đọc card UID
3. Gửi lên backend
4. Backend xử lý:
   - Thẻ mới → Tạo customer/vehicle/card
   - Thẻ cũ → Tạo session mới
5. Backend trả về success
6. ESP32:
   - Mở cổng
   - Beep success
   - Hiển thị "WELCOME"
7. Sau 5 giây → Tự động đóng cổng
8. Web dashboard cập nhật real-time
```

### Bước 3: Xe ra (CHECK-OUT)
```
1. Khách hàng quét thẻ RFID (lần 2)
2. ESP32 gửi lên backend
3. Backend xử lý:
   - Tìm session đang mở
   - Đóng session
   - Tính phí đỗ xe
   - Cập nhật stats
4. Backend trả về success + parking_fee
5. ESP32:
   - Mở cổng
   - Beep success
   - Hiển thị "Tạm biệt"
6. Sau 5 giây → Tự động đóng cổng
7. Web dashboard cập nhật real-time
```

---

## 🎯 ĐIỂM MẠNH CỦA HỆ THỐNG

1. **Tự động hóa cao**
   - Tự động tạo customer/vehicle khi quét thẻ mới
   - Tự động check-in/check-out
   - Tự động đóng cổng

2. **Xử lý lỗi tốt**
   - Wi-Fi auto-reconnect
   - Offline mode
   - API timeout & retry

3. **Real-time monitoring**
   - Web dashboard cập nhật mỗi 5 giây
   - Thống kê chi tiết
   - Lịch sử đầy đủ

4. **Dễ mở rộng**
   - RESTful API
   - JSON database (dễ migrate sang SQL)
   - Modular code structure

5. **User-friendly**
   - LCD hiển thị rõ ràng
   - Beep sound feedback
   - Web UI đẹp và dễ dùng

---

**Tài liệu này mô tả chi tiết toàn bộ hệ thống Smart Parking!**
