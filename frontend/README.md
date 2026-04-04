# SmartParking Frontend

Simple student-friendly frontend for the SmartParking backend.

## Stack
- React + Vite + TypeScript
- React Router
- Axios

## Setup
```bash
cd /home/khuong/projects/SmartParking/frontend
cp .env.example .env
npm install
npm run dev
```

App runs at: <http://127.0.0.1:5173>

Backend API expected at: `http://127.0.0.1:8000/api/v1`

## Seed login
- admin / admin123
- staff01 / staff123

## Main pages
- Dashboard
- Customers
- Vehicles
- RFID Cards
- Monthly Plans
- Monthly Subscriptions
- Parking Sessions (check-in / check-out)
- Payments
- Devices
- Alerts

## Build
```bash
npm run build
npm run preview
```
