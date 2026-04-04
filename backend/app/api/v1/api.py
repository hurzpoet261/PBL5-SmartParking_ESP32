from fastapi import APIRouter

from app.api.v1.endpoints import (
    alerts,
    auth,
    customers,
    dashboard,
    devices,
    monthly_plans,
    monthly_subscriptions,
    parking_sessions,
    payments,
    rfid_cards,
    vehicles,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["Vehicles"])
api_router.include_router(rfid_cards.router, prefix="/rfid-cards", tags=["RFID Cards"])
api_router.include_router(monthly_plans.router, prefix="/monthly-plans", tags=["Monthly Plans"])
api_router.include_router(
    monthly_subscriptions.router,
    prefix="/monthly-subscriptions",
    tags=["Monthly Subscriptions"],
)
api_router.include_router(
    parking_sessions.router,
    prefix="/parking-sessions",
    tags=["Parking Sessions"],
)
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
