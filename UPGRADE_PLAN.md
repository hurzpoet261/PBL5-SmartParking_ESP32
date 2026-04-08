# 🚀 KẾ HOẠCH NÂNG CẤP HỆ THỐNG SMART PARKING V3.0

## 📋 YÊU CẦU MỚI

### 1. Database
- ❌ JSON file (cũ)
- ✅ MongoDB (mới)

### 2. Kiến trúc
- ❌ Flat structure (cũ)
- ✅ MVC Pattern (mới)

### 3. Chức năng mới
- ✅ Đăng ký thẻ xe mới (có form đầy đủ)
- ✅ Gói trả phí: Theo ngày, Theo tháng, Theo lượt
- ✅ Map chỗ đỗ xe (visual parking slots)
- ✅ Thống kê doanh thu (biểu đồ)
- ✅ Quản lý khách hàng đầy đủ
- ✅ Quản lý gói cước
- ✅ Lịch sử giao dịch

### 4. Giao diện
- ✅ Dashboard với biểu đồ
- ✅ Trang đăng ký thẻ
- ✅ Trang quản lý khách hàng
- ✅ Trang quản lý xe
- ✅ Trang map chỗ đỗ
- ✅ Trang thống kê doanh thu
- ✅ Trang cài đặt

## 🏗️ CẤU TRÚC MỚI (MVC)

```
PBL5-SmartParking_ESP32/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # Entry point
│   │   │
│   │   ├── models/              # Models (M)
│   │   │   ├── __init__.py
│   │   │   ├── customer.py
│   │   │   ├── vehicle.py
│   │   │   ├── rfid_card.py
│   │   │   ├── session.py
│   │   │   ├── parking_slot.py
│   │   │   ├── package.py
│   │   │   └── transaction.py
│   │   │
│   │   ├── controllers/         # Controllers (C)
│   │   │   ├── __init__.py
│   │   │   ├── rfid_controller.py
│   │   │   ├── customer_controller.py
│   │   │   ├── vehicle_controller.py
│   │   │   ├── session_controller.py
│   │   │   ├── slot_controller.py
│   │   │   ├── package_controller.py
│   │   │   ├── stats_controller.py
│   │   │   └── transaction_controller.py
│   │   │
│   │   ├── services/            # Business Logic
│   │   │   ├── __init__.py
│   │   │   ├── rfid_service.py
│   │   │   ├── customer_service.py
│   │   │   ├── vehicle_service.py
│   │   │   ├── session_service.py
│   │   │   ├── slot_service.py
│   │   │   ├── package_service.py
│   │   │   ├── fee_calculator.py
│   │   │   └── stats_service.py
│   │   │
│   │   ├── database/            # Database
│   │   │   ├── __init__.py
│   │   │   ├── mongodb.py
│   │   │   └── seed_data.py
│   │   │
│   │   ├── schemas/             # Pydantic Schemas
│   │   │   ├── __init__.py
│   │   │   ├── customer_schema.py
│   │   │   ├── vehicle_schema.py
│   │   │   ├── session_schema.py
│   │   │   └── package_schema.py
│   │   │
│   │   ├── config/              # Configuration
│   │   │   ├── __init__.py
│   │   │   └── settings.py
│   │   │
│   │   └── utils/               # Utilities
│   │       ├── __init__.py
│   │       ├── id_generator.py
│   │       └── date_utils.py
│   │
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                    # Views (V)
│   ├── index.html              # Dashboard
│   ├── pages/
│   │   ├── customers.html      # Quản lý khách hàng
│   │   ├── vehicles.html       # Quản lý xe
│   │   ├── register-card.html  # Đăng ký thẻ mới
│   │   ├── packages.html       # Quản lý gói cước
│   │   ├── parking-map.html    # Map chỗ đỗ
│   │   ├── sessions.html       # Lịch sử ra vào
│   │   ├── revenue.html        # Thống kê doanh thu
│   │   └── settings.html       # Cài đặt
│   │
│   ├── assets/
│   │   ├── css/
│   │   │   ├── main.css
│   │   │   ├── dashboard.css
│   │   │   └── parking-map.css
│   │   │
│   │   ├── js/
│   │   │   ├── main.js
│   │   │   ├── api.js
│   │   │   ├── dashboard.js
│   │   │   ├── customers.js
│   │   │   ├── parking-map.js
│   │   │   ├── revenue-chart.js
│   │   │   └── utils.js
│   │   │
│   │   └── images/
│   │       └── logo.png
│   │
│   └── components/             # Reusable components
│       ├── navbar.html
│       ├── sidebar.html
│       └── modal.html
│
├── firmware/                   # ESP32 (không đổi)
│   ├── esp32_config.py
│   ├── esp32_main.py
│   ├── mfrc522.py
│   └── lcd_i2c.py
│
├── scripts/
│   ├── start_backend.bat
│   ├── start_frontend.bat
│   └── setup_mongodb.bat
│
└── docs/
    └── ...
```

## 📊 DATABASE SCHEMA (MongoDB)

### Collections:

1. **customers** - Khách hàng
2. **vehicles** - Xe
3. **rfid_cards** - Thẻ RFID
4. **sessions** - Phiên đỗ xe
5. **parking_slots** - Chỗ đỗ xe
6. **packages** - Gói cước
7. **transactions** - Giao dịch thanh toán
8. **settings** - Cài đặt hệ thống

## 🎨 GIAO DIỆN MỚI

### 1. Dashboard
- Thống kê tổng quan (cards)
- Biểu đồ doanh thu (Chart.js)
- Biểu đồ lượt ra vào
- Danh sách xe đang đỗ
- Hoạt động gần đây

### 2. Đăng ký thẻ mới
- Form đầy đủ: Tên, SĐT, Email, CMND
- Thông tin xe: Biển số, Loại xe, Màu
- Chọn gói cước: Lượt, Ngày, Tháng
- Quét thẻ RFID
- Preview & Submit

### 3. Map chỗ đỗ xe
- Grid layout (có thể config số hàng/cột)
- Màu sắc: Trống (xanh), Đang đỗ (đỏ), Reserved (vàng)
- Click vào slot → Xem thông tin xe
- Real-time update

### 4. Thống kê doanh thu
- Biểu đồ cột: Doanh thu theo ngày/tháng
- Biểu đồ tròn: Phân loại theo gói cước
- Bảng chi tiết giao dịch
- Export Excel/PDF

## 🔧 TÍNH NĂNG MỚI

### 1. Gói cước
- **Lượt**: Tính phí mỗi lần ra vào
- **Ngày**: Trả cố định theo ngày (VD: 50k/ngày)
- **Tháng**: Trả cố định theo tháng (VD: 500k/tháng)

### 2. Tính phí thông minh
- Kiểm tra gói cước còn hạn không
- Tự động gia hạn hoặc chuyển sang lượt
- Tính phí theo thời gian thực

### 3. Quản lý chỗ đỗ
- Tự động assign slot khi check-in
- Release slot khi check-out
- Đặt chỗ trước (reserved)

## 📅 TIMELINE

### Phase 1: Backend MVC (2-3 giờ)
- Setup MongoDB
- Tạo Models
- Tạo Controllers
- Tạo Services
- API Endpoints

### Phase 2: Frontend (2-3 giờ)
- Dashboard với biểu đồ
- Các trang quản lý
- Map chỗ đỗ
- Form đăng ký

### Phase 3: Integration (1 giờ)
- Kết nối Frontend-Backend
- Test toàn bộ
- Fix bugs

### Phase 4: Documentation (30 phút)
- Update docs
- API documentation
- User guide

## 🚀 BẮT ĐẦU NGAY!

Tôi sẽ bắt đầu với Phase 1: Backend MVC
