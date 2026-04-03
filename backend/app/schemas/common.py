from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ORMBaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class MessageResponse(BaseModel):
    message: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DashboardMetric(BaseModel):
    label: str
    value: int | Decimal | float


class RevenuePoint(BaseModel):
    date: date
    revenue: Decimal


class DashboardOverviewResponse(BaseModel):
    total_customers: int
    total_vehicles_inside: int
    open_alerts: int
    online_devices: int
    today_revenue: Decimal
    monthly_revenue: Decimal
    occupancy_rate: float
    recent_alerts: list[dict]
