# 🔧 Hướng dẫn khắc phục sự cố - Smart Parking System

## 🚨 Các lỗi thường gặp và cách fix

### 1. ❌ Lỗi: "psql is not recognized"

**Nguyên nhân**: PostgreSQL chưa được cài đặt hoặc chưa thêm vào PATH

**Giải pháp**:
```bash
# Tải và cài PostgreSQL từ:
https://www.postgresql.org/download/windows/

# Hoặc dùng Docker:
docker run -d -p 5432:5432 ^
  -e POSTGRES_PASSWORD=2201 ^
  -e POSTGRES_DB=smart_parking ^
  --name postgres-parking ^
  postgres:15
```

---

### 2. ❌ Lỗi: "could not connect to server"

**Nguyên nhân**: PostgreSQL chưa chạy hoặc sai thông tin kết nối

**Giải pháp**:
1. Kiểm tra PostgreSQL đang chạy:
   - Windows Services → PostgreSQL → Start
   - Hoặc: `docker start postgres-parking`

2. Kiểm tra file `backend/.env`:
   ```env
   POSTGRES_PASSWORD=2201  # Đúng với password của bạn
   POSTGRES_DB=smart_parking
   ```

3. Tạo database nếu chưa có:
   ```sql
   CREATE DATABASE smart_parking;
   ```

---

### 3. ❌ Lỗi: "ModuleNotFoundError: No module named 'app'"

**Nguyên nhân**: Chạy backend từ sai thư mục

**Giải pháp**:
```bash
# Phải chạy từ thư mục backend
cd backend
.\run.bat

# KHÔNG chạy từ thư mục gốc
```

---

### 4. ❌ Lỗi: "CORS policy: No 'Access-Control-Allow-Origin'"

**Nguyên nhân**: Backend chưa cấu hình CORS đúng

**Giải pháp**:
1. Kiểm tra `backend/.env`:
   ```env
   BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:8000"]
   ```

2. Restart backend:
   - Ctrl+C trong terminal backend
   - Chạy lại: `.\run.bat`

---

### 5. ❌ Lỗi: "Port 8000 already in use"

**Nguyên nhân**: Backend đã chạy ở terminal khác

**Giải pháp**:
```bash
# Tìm process đang dùng port 8000
netstat -ano | findstr :8000

# Kill process (thay <PID> bằng số thực tế)
taskkill /PID <PID> /F
```

---

### 6. ❌ Lỗi: "Port 5173 already in use"

**Nguyên nhân**: Frontend đã chạy ở terminal khác

**Giải pháp**:
- Vite sẽ tự động dùng port 5174
- Hoặc kill process:
  ```bash
  netstat -ano | findstr :5173
  taskkill /PID <PID> /F
  ```

---

### 7. ❌ Lỗi: "npm: command not found"

**Nguyên nhân**: Node.js chưa cài đặt

**Giải pháp**:
```bash
# Tải và cài Node.js từ:
https://nodejs.org/

# Kiểm tra sau khi cài:
node --version
npm --version
```

---

### 8. ❌ Lỗi: "python: command not found"

**Nguyên nhân**: Python chưa cài đặt hoặc chưa thêm vào PATH

**Giải pháp**:
```bash
# Tải và cài Python 3.12 từ:
https://www.python.org/downloads/

# Nhớ check "Add Python to PATH" khi cài

# Kiểm tra:
python --version
```

---

### 9. ❌ Frontend không hiển thị sau khi login

**Nguyên nhân**: Cache trình duyệt hoặc token cũ

**Giải pháp**:
1. Xóa cache trình duyệt:
   - Ctrl+Shift+Delete
   - Chọn "All time"
   - Clear data

2. Xóa localStorage:
   - F12 → Console
   - Gõ: `localStorage.clear()`
   - Refresh (F5)

---

### 10. ❌ Lỗi: "alembic: command not found"

**Nguyên nhân**: Virtual environment chưa được activate

**Giải pháp**:
```bash
cd backend
.\venv\Scripts\activate
alembic upgrade head
```

---

### 11. ❌ Lỗi: "ValidationError" khi start backend

**Nguyên nhân**: File `.env` thiếu hoặc sai format

**Giải pháp**:
1. Copy từ example:
   ```bash
   cd backend
   copy .env.example .env
   ```

2. Kiểm tra format JSON trong BACKEND_CORS_ORIGINS:
   ```env
   BACKEND_CORS_ORIGINS=["http://localhost:5173"]
   ```
   (Phải có dấu ngoặc vuông và quotes)

---

### 12. ❌ ESP32 không kết nối Wi-Fi

**Nguyên nhân**: Sai SSID/password trong `firmware/config.py`

**Giải pháp**:
```python
# Sửa file firmware/config.py
WIFI_SSID = "Ten_WiFi_Cua_Ban"
WIFI_PASS = "Mat_Khau_WiFi"
```

---

## 🔍 Kiểm tra hệ thống

### Kiểm tra Backend
```bash
# Health check
curl http://localhost:8000/health

# Hoặc mở trình duyệt:
http://localhost:8000/docs
```

### Kiểm tra Frontend
```bash
# Mở trình duyệt:
http://localhost:5173
```

### Kiểm tra Database
```bash
# Chạy script kiểm tra
CHECK_DB_FIXED.bat
```

---

## 📞 Cần thêm trợ giúp?

1. Kiểm tra logs trong terminal
2. Xem API docs: http://localhost:8000/docs
3. Kiểm tra file `.env` có đúng format không
4. Đảm bảo tất cả services đang chạy:
   - PostgreSQL
   - Backend (port 8000)
   - Frontend (port 5173)

---

## ✅ Checklist trước khi chạy

- [ ] PostgreSQL đã cài và đang chạy
- [ ] Database `smart_parking` đã được tạo
- [ ] Python 3.12+ đã cài
- [ ] Node.js 20+ đã cài
- [ ] File `backend/.env` đã tồn tại và đúng
- [ ] File `frontend/.env` đã tồn tại
- [ ] Đã chạy `setup.bat` thành công
- [ ] Backend chạy ở port 8000
- [ ] Frontend chạy ở port 5173

---

**Cập nhật**: April 2026
