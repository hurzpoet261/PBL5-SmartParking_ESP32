# 📖 HƯỚNG DẪN SỬ DỤNG - SMART PARKING V3.0

## 🚀 KHỞI ĐỘNG HỆ THỐNG

### 1. Kiểm tra MongoDB

```bash
cd backend_v3
python check_mongodb.py
```

### 2. Chạy Backend

```bash
cd backend_v3
python -m app.main
```

Backend chạy tại: http://localhost:8000

### 3. Mở Frontend

Mở file `frontend_v3/index.html` bằng trình duyệt hoặc Live Server

---

## 📝 ĐĂNG KÝ THẺ MỚI

### Cách 1: Tự động quét thẻ (Khuyên dùng)

1. Vào trang: http://localhost:5500/pages/register-card.html
2. Nhấn nút "Quét thẻ" (nút sẽ chuyển sang màu đỏ "Dừng quét")
3. Quét thẻ RFID trên ESP32
4. Mã thẻ sẽ TỰ ĐỘNG điền vào ô "UID Thẻ"
5. Điền thông tin khách hàng và xe
6. Chọn gói cước
7. Nhấn "Đăng ký"

### Cách 2: Nhập thủ công

1. Xem mã thẻ trên Serial Monitor ESP32
2. Copy mã thẻ (VD: 0xa3d6ce05)
3. Paste vào ô "UID Thẻ"
4. Điền thông tin và đăng ký

---

## 🎯 LUỒNG HOẠT ĐỘNG

### Đăng ký thẻ mới:
```
1. Nhấn "Quét thẻ" trên web
2. Quét thẻ RFID trên ESP32
3. Mã thẻ tự động hiện trên web (mỗi 2 giây check 1 lần)
4. Điền thông tin → Đăng ký
5. Thẻ sẵn sàng sử dụng
```

### Quét thẻ đã đăng ký:
```
1. Quét thẻ tại cổng
2. Nếu chưa có session → CHECK-IN (vào bãi)
3. Nếu đã có session → CHECK-OUT (ra bãi, tính phí)
4. Cổng tự động mở
```

---

## 🔧 KHẮC PHỤC SỰ CỐ

### Lỗi: Không đăng ký được

**Nguyên nhân:** CORS hoặc backend chưa chạy

**Giải pháp:**
1. Kiểm tra backend đã chạy: http://localhost:8000/health
2. Mở DevTools (F12) → Console để xem lỗi chi tiết
3. Restart backend

### Lỗi: Mã thẻ không tự động điền

**Nguyên nhân:** Chưa quét thẻ hoặc backend chưa nhận

**Giải pháp:**
1. Kiểm tra ESP32 đã kết nối WiFi
2. Quét lại thẻ RFID
3. Hoặc nhập thủ công

### Lỗi: MongoDB connection failed

**Giải pháp:**
```bash
# Chuyển sang MongoDB Local
copy .env.local .env
python -m app.main
```

---

## 📊 CẤU TRÚC DỰ ÁN

```
PBL5-SmartParking_ESP32/
├── backend_v3/          # Backend API
│   ├── app/
│   │   ├── controllers/ # API endpoints
│   │   ├── models/      # Data models
│   │   ├── services/    # Business logic
│   │   └── database/    # MongoDB connection
│   ├── .env            # Configuration
│   └── check_mongodb.py # MongoDB checker
│
├── frontend_v3/         # Web interface
│   ├── index.html      # Dashboard
│   ├── pages/          # All pages
│   └── assets/         # CSS, JS
│
├── firmware/            # ESP32 code
│   ├── esp32_main.py
│   ├── esp32_config.py
│   ├── mfrc522.py
│   └── lcd_i2c.py
│
├── docs/               # Documentation
└── scripts/            # Helper scripts
```

---

## ✅ CHECKLIST

- [ ] MongoDB đã chạy
- [ ] Backend đã chạy (http://localhost:8000)
- [ ] Frontend đã mở
- [ ] ESP32 đã kết nối WiFi (nếu có)
- [ ] Đã test đăng ký thẻ thành công

---

## 📞 HỖ TRỢ

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- MongoDB Check: `python check_mongodb.py`

**Chúc bạn thành công! 🚀**
