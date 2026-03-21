# PBL5-SmartParking_ESP32
# 🚗 PBL5: Hệ Thống Quản Lý Bãi Đỗ Xe Thông Minh (Smart Parking)

Dự án sử dụng công nghệ IoT (ESP32) kết hợp với Web App thuần Python để quản lý bãi đỗ xe tự động.

## 🌟 Tính Năng Chính
- **Quản lý xe:** Quét thẻ RFID RC522 để vào/ra bãi.
- **Giám sát an toàn:** Cảm biến khí Gas tự động báo động (Buzzer) và mở cửa thoát hiểm (Servo).
- **Giao diện Web:** Hiển thị trạng thái bãi xe và thống kê doanh thu (Chart.js).
- **Lưu trữ:** Dữ liệu được lưu an toàn trên MongoDB.

## 🛠 Cấu Trúc Phần Cứng (Pinout)
| Linh kiện | Chân ESP32 | Ghi chú |
|-----------|------------|---------|
| RFID RC522| 18, 19, 23, 5, 4 | Giao tiếp SPI |
| OLED SSD1306| 21, 22 | Giao tiếp I2C |
| Servo | 13 | Điều khiển cổng |
| Cảm biến Gas| 34 | Analog/Digital |
| Buzzer | 14 | Cảnh báo |

## 🚀 Hướng Dẫn Chạy Dự Án

### Bước 1: Chuẩn bị Môi trường
1. Cài đặt **MongoDB Community Server**.
2. Cài đặt các thư viện Python cần thiết trên máy tính:
   ```bash
   pip install flask pymongo paho-mqtt