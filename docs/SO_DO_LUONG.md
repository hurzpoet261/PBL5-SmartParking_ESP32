# 🔄 SƠ ĐỒ LUỒNG HỆ THỐNG SMART PARKING

## 📐 KIẾN TRÚC TỔNG QUAN

```
┌─────────────────────────────────────────────────────────────┐
│                    SMART PARKING SYSTEM                      │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│              │         │              │         │              │
│   ESP32      │◄───────►│   Backend    │◄───────►│     Web      │
│  (Firmware)  │  HTTP   │     API      │  HTTP   │  Dashboard   │
│              │         │              │         │              │
└──────┬───────┘         └──────┬───────┘         └──────────────┘
       │                        │
       │                        │
   Hardware                 Database
   ┌───┴────┐              (JSON File)
   │ RFID   │
   │ LCD    │
   │ Servo  │
   │ Sensor │
   └────────┘
```

---

## 🎯 LUỒNG 1: QUÉT THẺ RFID - XE VÀO (CHECK-IN)

```
┌─────────────────────────────────────────────────────────────────┐
│ BƯỚC 1: KHÁCH HÀNG QUÉT THẺ                                     │
└─────────────────────────────────────────────────────────────────┘

    👤 Khách hàng
     │
     │ Đưa thẻ RFID
     ▼
┌─────────────┐
│ RFID Reader │ ──► Đọc UID: "0xa3d6ce05"
│  (MFRC522)  │
└──────┬──────┘
       │
       ▼

┌─────────────────────────────────────────────────────────────────┐
│ BƯỚC 2: ESP32 XỬ LÝ                                            │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│ esp32_main.py        │
│ main() loop          │
└──────┬───────────────┘
       │
       │ reader.request()
       │ reader.anticoll()
       ▼
┌──────────────────────┐
│ Đọc được UID         │
│ card_id = 0xa3d6ce05 │
└──────┬───────────────┘
       │
       │ Kiểm tra cooldown (3s)
       ▼
┌──────────────────────┐
│ process_rfid_card()  │
└──────┬───────────────┘
       │
       │ 1. Bật LED
       │ 2. Hiển thị "SCANNING..." trên LCD
       │
       ▼

┌─────────────────────────────────────────────────────────────────┐
│ BƯỚC 3: GỬI REQUEST LÊN BACKEND                                │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│ send_rfid_scan()     │
└──────┬───────────────┘
       │
       │ HTTP POST
       │ URL: http://192.168.1.233:8000/api/v1/rfid/scan
       │
       │ Payload:
       │ {
       │   "card_uid": "0xa3d6ce05",
       │   "gate_id": 1,
       │   "distance_cm": 25.0,
       │   "timestamp": 1712217600
       │ }
       │
       ▼

┌─────────────────────────────────────────────────────────────────┐
│ BƯỚC 4: BACKEND XỬ LÝ                                          │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│ backend/app.py       │
│ @app.post("/rfid/scan")
└──────┬───────────────┘
       │
       │ 1. Nhận request
       │ 2. Load database
       ▼
┌──────────────────────┐
│ Kiểm tra card_uid    │
│ trong database?      │
└──────┬───────────────┘
       │
       ├─────── THẺ MỚI ──────────────────────────────────┐
       │                                                   │
       │ ┌──────────────────────────────────────────┐    │
       │ │ Tự động đăng ký:                         │    │
       │ │                                          │    │
       │ │ 1. Tạo Customer:                         │    │
       │ │    customer_id = "C000001"               │    │
       │ │    name = "Khách hàng C000001"           │    │
       │ │    customer_type = "walk_in"             │    │
       │ │                                          │    │
       │ │ 2. Tạo Vehicle:                          │    │
       │ │    vehicle_id = "V000001"                │    │
       │ │    plate_number = "XX-0001"              │    │
       │ │    vehicle_type = "motorbike"            │    │
       │ │                                          │    │
       │ │ 3. Tạo RFID Card:                        │    │
       │ │    card_uid = "0xa3d6ce05"               │    │
       │ │    status = "active"                     │    │
       │ │                                          │    │
       │ │ 4. Tạo Session (CHECK-IN):               │    │
       │ │    session_id = "S000001"                │    │
       │ │    entry_time = "2026-04-04T10:00:00"    │    │
       │ │    status = "in_progress"                │    │
       │ │                                          │    │
       │ │ 5. Cập nhật stats:                       │    │
       │ │    total_customers += 1                  │    │
       │ │    total_vehicles += 1                   │    │
       │ │    active_sessions += 1                  │    │
       │ │    total_entries += 1                    │    │
       │ │                                          │    │
       │ │ 6. Save database                         │    │
       │ └──────────────────────────────────────────┘    │
       │                                                   │
       └───────────────────────────────────────────────────┤
       │                                                   │
       ├─────── THẺ CŨ - CHƯA CÓ SESSION ─────────────────┤
       │                                                   │
       │ ┌──────────────────────────────────────────┐    │
       │ │ Check-in:                                │    │
       │ │                                          │    │
       │ │ 1. Lấy thông tin card từ database        │    │
       │ │ 2. Kiểm tra card status = "active"       │    │
       │ │ 3. Kiểm tra capacity (bãi đầy?)          │    │
       │ │                                          │    │
       │ │ 4. Tạo Session mới:                      │    │
       │ │    session_id = "S000002"                │    │
       │ │    entry_time = now                      │    │
       │ │    status = "in_progress"                │    │
       │ │                                          │    │
       │ │ 5. Cập nhật stats:                       │    │
       │ │    active_sessions += 1                  │    │
       │ │    total_entries += 1                    │    │
       │ │                                          │    │
       │ │ 6. Save database                         │    │
       │ └──────────────────────────────────────────┘    │
       │                                                   │
       └───────────────────────────────────────────────────┘
       │
       │ 7. Trả về response
       ▼
┌──────────────────────┐
│ Response:            │
│ {                    │
│   "success": true,   │
│   "action": "entry", │
│   "message": "Chào mừng!",
│   "customer_name": "Khách hàng C000001",
│   "vehicle_plate": "XX-0001",
│   "session_id": "S000001"
│ }                    │
└──────┬───────────────┘
       │
       ▼

┌─────────────────────────────────────────────────────────────────┐
│ BƯỚC 5: ESP32 XỬ LÝ RESPONSE                                   │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│ Nhận response        │
│ success = true       │
└──────┬───────────────┘
       │
       │ 1. Hiển thị LCD: "WELCOME!"
       │                  "Khách hàng C000001"
       │
       │ 2. Beep success (1500Hz, 100ms x2)
       │
       │ 3. Mở cổng
       ▼
┌──────────────────────┐
│ gate_open()          │
│ servo_angle(0)       │ ──► Servo quay 0°
└──────┬───────────────┘
       │
       │ Cổng mở
       │ gate_is_open = True
       │ gate_open_at = now
       │
       ▼

┌─────────────────────────────────────────────────────────────────┐
│ BƯỚC 6: TỰ ĐỘNG ĐÓNG CỔNG                                      │
└─────────────────────────────────────────────────────────────────┘

       │ Đợi 5 giây...
       │
       ▼
┌──────────────────────┐
│ Kiểm tra ultrasonic  │
│ get_distance()       │
└──────┬───────────────┘
       │
       ├─── distance < 30cm ───┐
       │                        │
       │ Có người gần           │
       │ → Giữ cổng mở          │
       │ → Reset timer          │
       │                        │
       └────────────────────────┤
       │                        │
       ├─── distance >= 30cm ───┤
       │                        │
       │ Không có người         │
       │ → Đóng cổng            │
       ▼                        │
┌──────────────────────┐       │
│ gate_close()         │       │
│ servo_angle(90)      │ ──► Servo quay 90°
└──────┬───────────────┘       │
       │                        │
       │ Hiển thị LCD:          │
       │ ">>> READY <<<"        │
       │ "Scan RFID Card"       │
       │                        │
       └────────────────────────┘
       │
       │ Tắt LED
       │ Sẵn sàng quét thẻ tiếp theo
       ▼
    [END]
```

---

## 🚪 LUỒNG 2: QUÉT THẺ RFID - XE RA (CHECK-OUT)

```
┌─────────────────────────────────────────────────────────────────┐
│ ĐIỀU KIỆN: Khách hàng đã check-in trước đó (có session mở)     │
└─────────────────────────────────────────────────────────────────┘

    👤 Khách hàng quét thẻ lần 2
     │
     ▼
┌──────────────────────┐
│ ESP32 đọc UID        │
│ card_id = 0xa3d6ce05 │
└──────┬───────────────┘
       │
       │ Gửi lên backend (tương tự bước trên)
       ▼

┌─────────────────────────────────────────────────────────────────┐
│ BACKEND XỬ LÝ - THẺ CŨ CÓ SESSION ĐANG MỞ                      │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│ Tìm session          │
│ status = "in_progress"│
│ card_uid = 0xa3d6ce05│
└──────┬───────────────┘
       │
       │ Tìm thấy session!
       ▼
┌──────────────────────────────────────────┐
│ CHECK-OUT:                               │
│                                          │
│ 1. Cập nhật session:                     │
│    exit_time = "2026-04-04T12:30:00"     │
│    status = "completed"                  │
│                                          │
│ 2. Tính phí đỗ xe:                       │
│    entry_time = 10:00                    │
│    exit_time = 12:30                     │
│    duration = 2.5 giờ                    │
│    fee = 3 giờ × 5000 = 15,000 VNĐ       │
│    (làm tròn lên)                        │
│                                          │
│ 3. Cập nhật stats:                       │
│    active_sessions -= 1                  │
│    total_exits += 1                      │
│    today_revenue += 15000                │
│                                          │
│ 4. Save database                         │
└──────┬───────────────────────────────────┘
       │
       │ Trả về response
       ▼
┌──────────────────────┐
│ Response:            │
│ {                    │
│   "success": true,   │
│   "action": "exit",  │
│   "message": "Tạm biệt!",
│   "parking_fee": 15000,
│   "duration_minutes": 150
│ }                    │
└──────┬───────────────┘
       │
       ▼

┌─────────────────────────────────────────────────────────────────┐
│ ESP32 XỬ LÝ                                                     │
└─────────────────────────────────────────────────────────────────┘

       │ 1. Hiển thị LCD: "Tạm biệt!"
       │                  "Phí: 15,000đ"
       │
       │ 2. Beep success
       │
       │ 3. Mở cổng
       │
       │ 4. Đợi 5 giây
       │
       │ 5. Tự động đóng cổng
       │
       ▼
    [END]
```

---

## 🌐 LUỒNG 3: WEB DASHBOARD - GIÁM SÁT REAL-TIME

```
┌─────────────────────────────────────────────────────────────────┐
│ NGƯỜI DÙNG MỞ WEB DASHBOARD                                     │
└─────────────────────────────────────────────────────────────────┘

    👤 Quản lý
     │
     │ Mở browser
     │ http://localhost/web/index.html
     ▼
┌──────────────────────┐
│ index.html load      │
└──────┬───────────────┘
       │
       │ DOMContentLoaded event
       ▼
┌──────────────────────┐
│ refreshAll()         │
└──────┬───────────────┘
       │
       │ Gọi 5 API endpoints song song
       │
       ├─── 1. GET /api/v1/stats ────────────────────┐
       │                                              │
       │    Response:                                 │
       │    {                                         │
       │      "total_customers": 10,                  │
       │      "total_vehicles": 12,                   │
       │      "active_sessions": 3,                   │
       │      "total_scans": 156                      │
       │    }                                         │
       │                                              │
       │    → Cập nhật 4 stat cards                   │
       │                                              │
       └──────────────────────────────────────────────┤
       │                                              │
       ├─── 2. GET /api/v1/sessions?limit=50 ────────┤
       │                                              │
       │    Response: Array of 50 sessions            │
       │    [                                         │
       │      {                                       │
       │        "session_id": "S000001",              │
       │        "customer_id": "C000001",             │
       │        "vehicle_id": "V000001",              │
       │        "card_uid": "0xa3d6ce05",             │
       │        "entry_time": "2026-04-04T10:00:00",  │
       │        "status": "in_progress"               │
       │      },                                      │
       │      ...                                     │
       │    ]                                         │
       │                                              │
       │    → Cập nhật bảng "Lịch sử ra vào"          │
       │                                              │
       └──────────────────────────────────────────────┤
       │                                              │
       ├─── 3. GET /api/v1/customers ─────────────────┤
       │                                              │
       │    → Cập nhật bảng "Khách hàng"              │
       │                                              │
       └──────────────────────────────────────────────┤
       │                                              │
       ├─── 4. GET /api/v1/vehicles ──────────────────┤
       │                                              │
       │    → Cập nhật bảng "Xe"                      │
       │                                              │
       └──────────────────────────────────────────────┤
       │                                              │
       ├─── 5. GET /api/v1/rfid-cards ────────────────┤
       │                                              │
       │    → Cập nhật bảng "Thẻ RFID"                │
       │                                              │
       └──────────────────────────────────────────────┘
       │
       │ Tất cả API thành công
       ▼
┌──────────────────────┐
│ setOnlineStatus(true)│
│ Status: ● Online     │
└──────┬───────────────┘
       │
       │ Hiển thị dữ liệu trên UI
       │
       ▼
┌──────────────────────┐
│ setInterval()        │
│ Refresh mỗi 5 giây   │
└──────┬───────────────┘
       │
       │ Loop vô hạn...
       │
       ▼
    [Cập nhật liên tục]


┌─────────────────────────────────────────────────────────────────┐
│ KHI BACKEND OFFLINE                                             │
└─────────────────────────────────────────────────────────────────┘

       │ API call failed
       ▼
┌──────────────────────┐
│ catch(error)         │
└──────┬───────────────┘
       │
       │ setOnlineStatus(false)
       │ Status: ● Offline
       │
       │ showError("Không thể kết nối Backend...")
       │
       ▼
    [Hiển thị lỗi]
```

---

## 🔄 LUỒNG 4: OFFLINE MODE (KHI MẤT INTERNET)

```
┌─────────────────────────────────────────────────────────────────┐
│ ESP32 MẤT KẾT NỐI WI-FI HOẶC BACKEND OFFLINE                   │
└─────────────────────────────────────────────────────────────────┘

    👤 Khách hàng quét thẻ
     │
     ▼
┌──────────────────────┐
│ ESP32 đọc UID        │
└──────┬───────────────┘
       │
       │ Gửi request lên backend
       ▼
┌──────────────────────┐
│ send_rfid_scan()     │
└──────┬───────────────┘
       │
       │ HTTP POST failed!
       │ (Timeout hoặc Connection Error)
       ▼
┌──────────────────────┐
│ return None          │
└──────┬───────────────┘
       │
       │ wifi_connected = False
       ▼
┌──────────────────────────────────────────┐
│ Kiểm tra OFFLINE_MODE_ENABLED            │
└──────┬───────────────────────────────────┘
       │
       ├─── OFFLINE_MODE_ENABLED = True ────────────┐
       │                                             │
       │ ┌────────────────────────────────────┐    │
       │ │ Kiểm tra thẻ trong danh sách       │    │
       │ │ OFFLINE_AUTHORIZED_CARDS           │    │
       │ │                                    │    │
       │ │ OFFLINE_AUTHORIZED_CARDS = [       │    │
       │ │   "0xa3d6ce05",                    │    │
       │ │   "0xcc40d906"                     │    │
       │ │ ]                                  │    │
       │ └────────┬───────────────────────────┘    │
       │          │                                 │
       │          ├─── Thẻ có trong list ──────┐   │
       │          │                             │   │
       │          │ ✅ Cho phép vào             │   │
       │          │ Hiển thị: "OFFLINE MODE"    │   │
       │          │ Mở cổng                     │   │
       │          │                             │   │
       │          └─────────────────────────────┤   │
       │          │                             │   │
       │          ├─── Thẻ KHÔNG có trong list ─┤   │
       │          │                             │   │
       │          │ ❌ Từ chối                  │   │
       │          │ Hiển thị: "NOT AUTHORIZED"  │   │
       │          │ Beep error                  │   │
       │          │                             │   │
       │          └─────────────────────────────┘   │
       │                                             │
       └─────────────────────────────────────────────┤
       │                                             │
       ├─── OFFLINE_MODE_ENABLED = False ────────────┤
       │                                             │
       │ ❌ Từ chối tất cả                           │
       │ Hiển thị: "NO CONNECTION"                   │
       │ Beep error                                  │
       │                                             │
       └─────────────────────────────────────────────┘
       │
       ▼
    [END]

┌─────────────────────────────────────────────────────────────────┐
│ TỰ ĐỘNG KẾT NỐI LẠI                                            │
└─────────────────────────────────────────────────────────────────┘

       │ Mỗi 30 giây
       ▼
┌──────────────────────┐
│ check_wifi_connection()
└──────┬───────────────┘
       │
       │ wlan.isconnected()?
       │
       ├─── False ─────────────┐
       │                        │
       │ Gọi connect_wifi()     │
       │ Thử kết nối lại        │
       │                        │
       └────────────────────────┤
       │                        │
       ├─── True ───────────────┤
       │                        │
       │ Đã kết nối             │
       │ Tiếp tục hoạt động     │
       │                        │
       └────────────────────────┘
```

---

## 📊 LUỒNG 5: TÍNH PHÍ ĐỖ XE

```
┌─────────────────────────────────────────────────────────────────┐
│ TÍNH PHÍ KHI CHECK-OUT                                          │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│ Session đang mở:     │
│ entry_time = 10:00   │
│ exit_time = 12:45    │
└──────┬───────────────┘
       │
       │ 1. Tính duration
       ▼
┌──────────────────────────────────────────┐
│ duration = exit_time - entry_time        │
│ duration = 2 giờ 45 phút                 │
│ duration_hours = 2.75 giờ                │
└──────┬───────────────────────────────────┘
       │
       │ 2. Làm tròn lên
       ▼
┌──────────────────────────────────────────┐
│ hours = ceil(2.75) = 3 giờ               │
└──────┬───────────────────────────────────┘
       │
       │ 3. Tính phí
       ▼
┌──────────────────────────────────────────┐
│ parking_fee_per_hour = 5,000 VNĐ         │
│ parking_fee = 3 × 5,000 = 15,000 VNĐ     │
└──────┬───────────────────────────────────┘
       │
       │ 4. Kiểm tra customer_type
       ▼
┌──────────────────────┐
│ customer_type?       │
└──────┬───────────────┘
       │
       ├─── "monthly" hoặc "vip" ───┐
       │                             │
       │ parking_fee = 0             │
       │ (Miễn phí)                  │
       │                             │
       └─────────────────────────────┤
       │                             │
       ├─── "walk_in" ───────────────┤
       │                             │
       │ parking_fee = 15,000        │
       │ (Tính phí bình thường)      │
       │                             │
       └─────────────────────────────┘
       │
       │ 5. Cập nhật stats
       ▼
┌──────────────────────────────────────────┐
│ today_revenue += parking_fee             │
└──────────────────────────────────────────┘
```

---

## 🎯 TỔNG KẾT CÁC LUỒNG CHÍNH

### 1. **Luồng Check-in (Xe vào)**
- Quét thẻ → ESP32 → Backend → Tạo/Tìm session → Mở cổng

### 2. **Luồng Check-out (Xe ra)**
- Quét thẻ → ESP32 → Backend → Đóng session + Tính phí → Mở cổng

### 3. **Luồng Tự động đóng cổng**
- Cổng mở → Đợi 5s → Kiểm tra ultrasonic → Đóng cổng

### 4. **Luồng Web Dashboard**
- Load page → Gọi API → Hiển thị dữ liệu → Auto refresh 5s

### 5. **Luồng Offline Mode**
- Mất kết nối → Kiểm tra authorized cards → Cho phép/Từ chối

### 6. **Luồng Auto-reconnect**
- Kiểm tra Wi-Fi mỗi 30s → Tự động kết nối lại nếu mất

---

**Tài liệu này mô tả chi tiết tất cả các luồng hoạt động của hệ thống!**
