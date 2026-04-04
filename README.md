# PBL5-SmartParking_ESP32

Frontend + Backend cho đồ án **Hệ thống quản lý bãi giữ xe thông minh**.

## Cấu trúc thư mục

```text
PBL5-SmartParking_ESP32/
├── backend/
├── frontend/
├── server/        # code cũ / phần khác của project
└── web/           # giao diện cũ / tài nguyên cũ
```

## Stack đang dùng

### Backend
- FastAPI
- SQLAlchemy 2.0
- Alembic
- PostgreSQL
- JWT auth

### Frontend
- React
- Vite
- TypeScript
- React Router
- Axios

---

# 1) Yêu cầu trước khi chạy

## Trên Windows
Cài sẵn:
- **Git**
- **Python 3.12**
- **Node.js 20+**
- **PostgreSQL** (chạy local, chưa cần Docker)

Khuyên dùng:
- **VS Code**
- **PowerShell**

## Trên Ubuntu / Linux
Cài sẵn:
- Git
- Python 3.12
- Node.js 20+
- PostgreSQL local

---

# 2) Tạo database PostgreSQL local

Tạo database tên:

```sql
CREATE DATABASE smart_parking;
```

Nếu bạn dùng user/password khác `postgres/postgres` thì chỉnh lại file `.env` backend.

---

# 3) Chạy backend

## Backend path

```bash
cd backend
```

## 3.1 Tạo file env

### Windows
```powershell
copy .env.example .env
```

### Ubuntu / Linux
```bash
cp .env.example .env
```

## 3.2 Sửa file `.env` nếu cần

Mặc định backend đọc các biến PostgreSQL local.

Ví dụ nên để như sau:

```env
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=smart_parking
```

> Nếu máy bạn đang dùng mật khẩu PostgreSQL khác, hãy sửa `POSTGRES_PASSWORD` cho đúng.

## 3.3 Tạo virtual environment và cài package

### Windows (PowerShell)
```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Nếu PowerShell chặn script, mở PowerShell bằng quyền admin rồi chạy 1 lần:

```powershell
Set-ExecutionPolicy RemoteSigned
```

### Ubuntu / Linux
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3.4 Chạy migration

```bash
alembic upgrade head
```

## 3.5 Seed dữ liệu mẫu

### Windows (PowerShell)
```powershell
$env:PYTHONPATH='.'
python scripts\seed_data.py
```

### Windows (CMD)
```cmd
set PYTHONPATH=.
python scripts\seed_data.py
```

### Ubuntu / Linux
```bash
PYTHONPATH=. python scripts/seed_data.py
```

## 3.6 Chạy backend

```bash
uvicorn app.main:app --reload
```

Backend chạy tại:
- API: <http://127.0.0.1:8000>
- Swagger: <http://127.0.0.1:8000/docs>

### Tài khoản test
- `admin / admin123`
- `staff01 / staff123`

---

# 4) Chạy frontend

## Frontend path

```bash
cd frontend
```

## 4.1 Tạo file env

### Windows
```powershell
copy .env.example .env
```

### Ubuntu / Linux
```bash
cp .env.example .env
```

## 4.2 Cài package

```bash
npm install
```

## 4.3 Chạy frontend

```bash
npm run dev
```

Frontend chạy tại:
- <http://127.0.0.1:5173>

Frontend mặc định gọi backend tại:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

---

# 5) Quy trình chạy nhanh nhất

## Terminal 1: backend

### Windows PowerShell
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### Ubuntu / Linux
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

## Terminal 2: frontend

```bash
cd frontend
npm run dev
```

---

# 6) Nếu clone mới hoàn toàn

Sau khi clone repo, chạy theo thứ tự:

1. Tạo database PostgreSQL `smart_parking`
2. Chạy backend:
   - tạo venv
   - cài requirements
   - copy `.env.example` -> `.env`
   - `alembic upgrade head`
   - seed data
   - `uvicorn app.main:app --reload`
3. Chạy frontend:
   - copy `.env.example` -> `.env`
   - `npm install`
   - `npm run dev`

---

# 7) Ghi chú

- Hiện tại project dùng **PostgreSQL local**, chưa cần Docker.
- Nếu backend không kết nối được DB, hãy kiểm tra lại:
  - PostgreSQL đã chạy chưa
  - user/password trong `backend/.env` có đúng không
  - database `smart_parking` đã được tạo chưa
- Nếu frontend login lỗi, hãy kiểm tra backend đã chạy ở `127.0.0.1:8000` chưa.

---

# 8) Lệnh ngắn gọn để gửi bạn cùng nhóm

## Backend
```bash
cd backend
copy .env.example .env   # hoặc cp trên Linux
py -3.12 -m venv venv    # Windows
pip install -r requirements.txt
alembic upgrade head
python scripts\seed_data.py
uvicorn app.main:app --reload
```

## Frontend
```bash
cd frontend
copy .env.example .env   # hoặc cp trên Linux
npm install
npm run dev
```
