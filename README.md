# 🚗 Smart Parking System

Hệ thống quản lý bãi đỗ xe thông minh sử dụng ESP32, RFID, và Web Dashboard.

## 📋 Tính năng

- ✅ Quét thẻ RFID tự động
- ✅ Tự động tạo khách hàng/xe khi quét thẻ mới
- ✅ Check-in/Check-out tự động
- ✅ Tính phí đỗ xe
- ✅ Web dashboard quản lý
- ✅ Thống kê real-time

## 🏗️ Cấu trúc dự án

```
PBL5-SmartParking_ESP32/
├── backend/          # Backend API (FastAPI)
├── firmware/         # ESP32 Firmware (MicroPython)
├── web/              # Web Dashboard
├── docs/             # Documentation
└── scripts/          # Utility scripts
```

## 🚀 Quick Start

### 1. Chạy Backend

```bash
# Windows
scripts\start_backend.bat

# Hoặc thủ công
cd backend
pip install -r requirements.txt
python app.py
```

### 2. Upload Firmware lên ESP32

**Cấu hình** (sửa `firmware/esp32_config.py`):
```python
WIFI_SSID = "Ten_WiFi"
WIFI_PASS = "Mat_Khau"
API_BASE_URL = "http://192.168.1.XXX:8000/api/v1"  # IP máy tính
```

**Upload** (sử dụng Thonny IDE):
- `mfrc522.py`
- `lcd_i2c.py`
- `esp32_config.py`
- `esp32_main.py` → đổi tên thành `main.py`

### 3. Mở Web Dashboard

```bash
# Mở file
web\index.html

# Hoặc chạy toàn bộ
scripts\start_system.bat
```

## 📚 Documentation

Xem hướng dẫn đầy đủ: [`docs/GUIDE.md`](docs/GUIDE.md)

## 🔧 Tech Stack

- **Backend**: FastAPI + Python
- **Frontend**: HTML/CSS/JavaScript
- **Firmware**: MicroPython
- **Hardware**: ESP32 + MFRC522 + LCD I2C + Servo

## 📊 API Endpoints

- `POST /api/v1/rfid/scan` - Quét thẻ RFID
- `GET /api/v1/customers` - Danh sách khách hàng
- `GET /api/v1/vehicles` - Danh sách xe
- `GET /api/v1/sessions` - Lịch sử ra vào
- `GET /api/v1/stats` - Thống kê

API Docs: http://localhost:8000/docs

## 🧪 Testing

```bash
# Test backend
curl http://localhost:8000/health

# Test tạo dữ liệu
curl -X POST "http://localhost:8000/api/v1/test/scan?card_uid=TEST001"
```

## 📝 License

MIT License

## 👥 Contributors

Smart Parking Development Team

---

**Version**: 2.0.0  
**Last Updated**: April 2026
