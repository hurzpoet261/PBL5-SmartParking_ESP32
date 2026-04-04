# 🚗 Smart Parking System - Complete Guide

**Version**: 0.1.0  
**Status**: ✅ Production Ready  
**Last Updated**: April 2026

---

## 📋 Project Structure

```
PBL5-SmartParking_ESP32/
├── backend/                 # FastAPI Backend (Port 8000)
│   ├── app/
│   │   ├── main.py         # FastAPI app
│   │   ├── core/           # Config, DB, Security
│   │   ├── api/v1/         # API Endpoints
│   │   ├── models/         # SQLAlchemy ORM
│   │   └── schemas/        # Pydantic schemas
│   ├── alembic/            # Database migrations
│   ├── scripts/            # seed_data.py
│   ├── requirements.txt    # Python dependencies
│   └── run.bat            # Start script
│
├── frontend/                # React + Vite (Port 5173)
│   ├── src/
│   │   ├── pages/          # Page components
│   │   ├── components/     # Reusable components
│   │   ├── api/            # API client
│   │   ├── context/        # Auth context
│   │   └── router/         # Route config
│   ├── package.json        # Node dependencies
│   └── vite.config.ts      # Vite config
│
├── firmware/                # ESP32 MicroPython Firmware
│   ├── main.py            # Main program
│   ├── config.py          # Wi-Fi, MQTT config
│   ├── mfrc522.py         # RFID reader driver
│   └── lcd_i2c.py         # LCD driver
│
└── setup.bat              # Complete setup script
```

---

## 🚀 Quick Start (Windows)

### **Option 1: Automatic Setup (Recommended)**

```bash
# 1. Double-click setup.bat
#    or run in terminal:
E:\PBL5-SmartParking_ESP32\setup.bat

# 2. This will:
#    - Install backend dependencies
#    - Apply database migrations
#    - Seed admin account (admin/admin123)
#    - Install frontend dependencies
```

### **Option 2: Manual Setup**

#### **Backend Setup**
```bash
# 1. Navigate to backend
cd E:\PBL5-SmartParking_ESP32\backend

# 2. Activate virtual environment
.\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Apply database migrations
alembic upgrade head

# 5. Seed database
python -c "from scripts.seed_data import seed; seed()"

# 6. Start server
.\run.bat
```

#### **Frontend Setup**
```bash
# 1. Navigate to frontend (NEW TERMINAL)
cd E:\PBL5-SmartParking_ESP32\frontend

# 2. Install dependencies
npm install

# 3. Start dev server
npm run dev
```

---

## 🔑 Default Credentials

| Field | Value |
|-------|-------|
| **Username** | `admin` |
| **Password** | `admin123` |
| **Role** | Administrator |

> ⚠️ Change these credentials in production!

---

## 🌐 Access Points

| Service | URL | Status |
|---------|-----|--------|
| **Frontend** | http://localhost:5173 | 🟢 Ready |
| **Backend API** | http://localhost:8000/api/v1 | 🟢 Ready |
| **API Docs** | http://localhost:8000/docs | 📚 Swagger |
| **Health Check** | http://localhost:8000/health | 🏥 System status |

---

## 🗄️ Database Setup

### **Required: PostgreSQL**

```bash
# Windows Installation Options:

# Option 1: pgAdmin Download
# https://www.postgresql.org/download/windows/

# Option 2: Docker (Recommended)
docker run -d -p 5432:5432 ^
  -e POSTGRES_PASSWORD=2201 ^
  -e POSTGRES_DB=smart_parking ^
  --name postgres-parking ^
  postgres:15
```

### **Verify Connection**
```bash
# Check .env file
E:\PBL5-SmartParking_ESP32\backend\.env

# Should have:
DATABASE_URL=postgresql://postgres:2201@localhost:5432/smart_parking
```

---

## 🔧 Backend Environment Variables

Edit `.env` file:

```env
APP_NAME=Smart Parking Backend
APP_VERSION=0.1.0
DEBUG=true
API_V1_PREFIX=/api/v1

# PostgreSQL
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=2201
POSTGRES_DB=smart_parking

DATABASE_URL=postgresql://postgres:2201@localhost:5432/smart_parking

# JWT
SECRET_KEY=change_this_to_a_very_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS Origins
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:5174","http://localhost:8000"]
```

---

## 📱 Frontend Environment Variables

Edit `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

---

## 🧪 API Testing

### **Test with cURL**

```bash
# 1. Health Check
curl http://localhost:8000/health

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"admin\",\"password\":\"admin123\"}"

# 3. Get Current User (requires token)
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### **Interactive Testing**
Open Swagger UI at: http://localhost:8000/docs

---

## 🐛 Troubleshooting

### **❌ "ModuleNotFoundError: No module named 'app'"**
```bash
# Solution: Run from backend directory
cd E:\PBL5-SmartParking_ESP32\backend
.\run.bat
```

### **❌ "CORS policy: No 'Access-Control-Allow-Origin' header"**
```bash
# Solution: Restart backend after .env changes
# 1. Press Ctrl+C in backend terminal
# 2. Start again: .\run.bat
```

### **❌ "psycopg2.OperationalError: could not connect to server"**
```bash
# Solution: Start PostgreSQL
# Windows:
#   - pgAdmin → Right-click server → Start
#   or
#   - Services → PostgreSQL → Start
# Docker:
#   docker start postgres-parking
```

### **❌ "Port 5173 already in use"**
```bash
# Solution: Vite will auto-use next port (5174)
# or kill process:
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

### **❌ Frontend won't show after login**
```bash
# Clear browser cache:
# 1. Ctrl+Shift+Delete
# 2. Select "All time"
# 3. Clear data
# 4. Refresh page (F5)
```

---

## 📊 Database Management

### **View Database**
```bash
# Connect to database
psql -U postgres -d smart_parking

# Common queries:
SELECT * FROM staff_users;
SELECT * FROM parking_sessions;
SELECT * FROM payments;
```

### **Reset Database**
```bash
# Drop and recreate
dropdb -U postgres smart_parking
createdb -U postgres smart_parking

# Then re-migrate:
alembic upgrade head
python -c "from scripts.seed_data import seed; seed()"
```

### **Backup Database**
```bash
pg_dump -U postgres smart_parking > backup.sql
```

---

## 📦 Available API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/login` | User login |
| `GET` | `/auth/me` | Get current user |
| `GET` | `/dashboard/summary` | Dashboard overview |
| `GET` | `/customers` | List customers |
| `POST` | `/customers` | Create customer |
| `GET` | `/vehicles` | List vehicles |
| `GET` | `/parking-sessions` | List sessions |
| `POST` | `/parking-sessions/check-in` | Vehicle check-in |
| `POST` | `/parking-sessions/check-out` | Vehicle check-out |
| `GET` | `/payments` | List payments |
| `GET` | `/alerts` | List alerts |
| `GET` | `/devices` | List devices |

> Full API documentation at: http://localhost:8000/docs

---

##  Firmware (ESP32)

### **Upload to ESP32**
```bash
# Using WebREPL (Recommended):
# 1. Connect USB cable
# 2. Open: http://micropython.org/webrepl/
# 3. Upload files:
#    - config.py
#    - wifi_mqtt.py
#    - mfrc522.py
#    - lcd_i2c.py
#    - main.py
# 4. Restart ESP32
```

### **Update Wi-Fi Credentials**
Edit `firmware/config.py`:
```python
WIFI_SSID = "Your_WiFi_Name"
WIFI_PASS = "Your_WiFi_Password"
```

---

## 🔄 Deployment Ready

### **Production Deployment Checklist**

- [ ] Change `SECRET_KEY` in `.env`
- [ ] Set `DEBUG=false`
- [ ] Update `BACKEND_CORS_ORIGINS` to production domain
- [ ] Use strong PostgreSQL password
- [ ] Enable HTTPS/SSL
- [ ] Setup firewall rules
- [ ] Configure backup strategy
- [ ] Setup monitoring/logging

---

## 📚 Technologies

- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: React 18, TypeScript, Vite
- **Database**: PostgreSQL 15
- **Authentication**: JWT (python-jose)
- **Firmware**: MicroPython, ESP32

---

## 🆘 Support

| Issue | Solution |
|-------|----------|
| Need help? | Check `/docs` endpoint |
| Question? | Review `.env` file |
| Error logs? | Check terminal output |
| DB error? | Verify PostgreSQL running |

---

## ✅ Quick Checklist

- [x] Backend configured
- [x] Frontend configured
- [x] Database migrations applied
- [x] Admin account created
- [x] CORS properly configured
- [x] API endpoints working

**Status: READY TO USE! 🎉**

---

**Last Verified**: April 3, 2026
**By**: Smart Parking Development Team

