# 📚 TÀI LIỆU DỰ ÁN SMART PARKING

## 📖 Danh sách tài liệu

### 1. [GUIDE.md](GUIDE.md) - Hướng dẫn sử dụng đầy đủ
**Dành cho:** Người mới bắt đầu, người setup hệ thống

**Nội dung:**
- ✅ Giới thiệu hệ thống
- ✅ Yêu cầu phần cứng/phần mềm
- ✅ Hướng dẫn cài đặt từng bước
- ✅ Cấu hình Wi-Fi và API
- ✅ Upload firmware lên ESP32
- ✅ Troubleshooting & FAQ

**Đọc file này nếu:** Bạn muốn setup và chạy hệ thống

---

### 2. [PHAN_TICH_DU_AN.md](PHAN_TICH_DU_AN.md) - Phân tích chi tiết dự án
**Dành cho:** Developer, người muốn hiểu sâu về hệ thống

**Nội dung:**
- ✅ Tổng quan kiến trúc hệ thống
- ✅ Cấu trúc dự án chi tiết
- ✅ Phân tích từng file (backend, firmware, web)
- ✅ Database structure
- ✅ API endpoints đầy đủ
- ✅ Logic nghiệp vụ
- ✅ Bảo mật & xử lý lỗi
- ✅ Quy trình hoạt động hoàn chỉnh

**Đọc file này nếu:** Bạn muốn hiểu cách hệ thống hoạt động

---

### 3. [SO_DO_LUONG.md](SO_DO_LUONG.md) - Sơ đồ luồng chi tiết
**Dành cho:** Developer, người muốn hiểu luồng xử lý

**Nội dung:**
- ✅ Kiến trúc tổng quan (diagram)
- ✅ Luồng 1: Quét thẻ - Xe vào (CHECK-IN)
- ✅ Luồng 2: Quét thẻ - Xe ra (CHECK-OUT)
- ✅ Luồng 3: Web Dashboard - Giám sát real-time
- ✅ Luồng 4: Offline Mode
- ✅ Luồng 5: Tính phí đỗ xe
- ✅ Luồng tự động đóng cổng

**Đọc file này nếu:** Bạn muốn xem sơ đồ luồng xử lý

---

### 4. [CHUC_NANG_FILE.md](CHUC_NANG_FILE.md) - Chức năng từng file
**Dành cho:** Developer, người muốn tìm hiểu từng file

**Nội dung:**
- ✅ Chức năng chi tiết từng file
- ✅ Backend files (app.py, config.py, ...)
- ✅ Firmware files (esp32_main.py, esp32_config.py, ...)
- ✅ Web files (index.html, app.js, style.css)
- ✅ Scripts files (start_backend.bat, ...)
- ✅ Tóm tắt theo vai trò (files cần sửa, chạy, đọc)

**Đọc file này nếu:** Bạn muốn biết file nào làm gì

---

## 🎯 Nên đọc theo thứ tự nào?

### Nếu bạn là người MỚI:
```
1. README.md (root folder) - Tổng quan nhanh
2. docs/GUIDE.md - Hướng dẫn setup chi tiết
3. docs/CHUC_NANG_FILE.md - Hiểu từng file làm gì
```

### Nếu bạn là DEVELOPER:
```
1. docs/PHAN_TICH_DU_AN.md - Hiểu kiến trúc & logic
2. docs/SO_DO_LUONG.md - Xem sơ đồ luồng
3. docs/CHUC_NANG_FILE.md - Tham khảo từng file
4. Source code - Đọc code chi tiết
```

### Nếu bạn muốn TROUBLESHOOT:
```
1. docs/GUIDE.md - Phần Troubleshooting
2. docs/PHAN_TICH_DU_AN.md - Phần Bảo mật & Xử lý lỗi
3. Backend logs - Xem lỗi từ server
4. ESP32 serial monitor - Xem lỗi từ firmware
```

---

## 📁 Cấu trúc thư mục docs/

```
docs/
├── README.md                  # File này - Danh mục tài liệu
├── GUIDE.md                   # Hướng dẫn sử dụng đầy đủ
├── PHAN_TICH_DU_AN.md        # Phân tích chi tiết dự án
├── SO_DO_LUONG.md            # Sơ đồ luồng chi tiết
└── CHUC_NANG_FILE.md         # Chức năng từng file
```

---

## 🔗 Liên kết nhanh

### Tài liệu chính:
- [README.md](../README.md) - Tài liệu chính (root folder)
- [CHANGELOG.md](../CHANGELOG.md) - Lịch sử thay đổi

### Source code:
- [backend/app.py](../backend/app.py) - Backend API
- [firmware/esp32_main.py](../firmware/esp32_main.py) - ESP32 firmware
- [firmware/esp32_config.py](../firmware/esp32_config.py) - ESP32 config
- [web/index.html](../web/index.html) - Web dashboard

### Scripts:
- [scripts/start_backend.bat](../scripts/start_backend.bat) - Chạy backend
- [scripts/start_system.bat](../scripts/start_system.bat) - Chạy toàn bộ

---

## 💡 Tips

### Khi đọc tài liệu:
- ✅ Đọc từ trên xuống dưới
- ✅ Chú ý các phần có ⚠️ (quan trọng)
- ✅ Thử nghiệm code examples
- ✅ Xem sơ đồ để hiểu luồng

### Khi gặp vấn đề:
- ✅ Kiểm tra logs (backend & ESP32)
- ✅ Đọc phần Troubleshooting trong GUIDE.md
- ✅ Kiểm tra cấu hình (esp32_config.py)
- ✅ Test từng component riêng lẻ

### Khi muốn mở rộng:
- ✅ Đọc PHAN_TICH_DU_AN.md để hiểu kiến trúc
- ✅ Xem SO_DO_LUONG.md để hiểu luồng
- ✅ Tham khảo API endpoints trong backend/app.py
- ✅ Thêm features mới theo pattern hiện tại

---

## 📞 Hỗ trợ

Nếu có thắc mắc:
1. Đọc FAQ trong GUIDE.md
2. Kiểm tra Troubleshooting
3. Xem logs để debug
4. Liên hệ team phát triển

---

**Chúc bạn thành công với dự án Smart Parking! 🚗**
