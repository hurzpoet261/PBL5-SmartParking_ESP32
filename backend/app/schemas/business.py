from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr

from app.models.enums import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    CardStatus,
    CardType,
    CustomerType,
    DeviceStatus,
    DeviceType,
    PaymentMethod,
    PaymentRecordStatus,
    PaymentStatus,
    SessionStatus,
    SubscriptionStatus,
    UserStatus,
    VehicleType,
)
from app.schemas.common import ORMBaseSchema


class CustomerCreate(BaseModel):
    customer_code: str
    full_name: str
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    customer_type: CustomerType = CustomerType.WALK_IN
    status: UserStatus = UserStatus.ACTIVE


class CustomerUpdate(BaseModel):
    customer_code: str | None = None
    full_name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    customer_type: CustomerType | None = None
    status: UserStatus | None = None


class CustomerResponse(ORMBaseSchema):
    customer_id: int
    customer_code: str
    full_name: str
    phone: str | None
    email: EmailStr | None
    address: str | None
    customer_type: CustomerType
    status: UserStatus
    created_at: datetime
    updated_at: datetime


class VehicleCreate(BaseModel):
    customer_id: int | None = None
    plate_number: str
    vehicle_type: VehicleType
    brand: str | None = None
    model: str | None = None
    color: str | None = None
    status: UserStatus = UserStatus.ACTIVE


class VehicleUpdate(BaseModel):
    customer_id: int | None = None
    plate_number: str | None = None
    vehicle_type: VehicleType | None = None
    brand: str | None = None
    model: str | None = None
    color: str | None = None
    status: UserStatus | None = None


class VehicleResponse(ORMBaseSchema):
    vehicle_id: int
    customer_id: int | None
    plate_number: str
    vehicle_type: VehicleType
    brand: str | None
    model: str | None
    color: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class RFIDCardCreate(BaseModel):
    card_uid: str
    card_code: str | None = None
    card_type: CardType
    assigned_customer_id: int | None = None
    assigned_vehicle_id: int | None = None
    issued_at: datetime | None = None
    expired_at: datetime | None = None
    status: CardStatus = CardStatus.AVAILABLE
    note: str | None = None


class RFIDCardUpdate(BaseModel):
    card_code: str | None = None
    card_type: CardType | None = None
    assigned_customer_id: int | None = None
    assigned_vehicle_id: int | None = None
    issued_at: datetime | None = None
    expired_at: datetime | None = None
    status: CardStatus | None = None
    note: str | None = None


class RFIDCardResponse(ORMBaseSchema):
    card_id: int
    card_uid: str
    card_code: str | None
    card_type: CardType
    assigned_customer_id: int | None
    assigned_vehicle_id: int | None
    issued_at: datetime | None
    expired_at: datetime | None
    status: CardStatus
    note: str | None
    created_at: datetime
    updated_at: datetime


class MonthlyPlanCreate(BaseModel):
    plan_name: str
    vehicle_type: VehicleType
    duration_months: int
    price: Decimal
    description: str | None = None
    status: UserStatus = UserStatus.ACTIVE


class MonthlyPlanUpdate(BaseModel):
    plan_name: str | None = None
    vehicle_type: VehicleType | None = None
    duration_months: int | None = None
    price: Decimal | None = None
    description: str | None = None
    status: UserStatus | None = None


class MonthlyPlanResponse(ORMBaseSchema):
    plan_id: int
    plan_name: str
    vehicle_type: VehicleType
    duration_months: int
    price: Decimal
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class MonthlySubscriptionCreate(BaseModel):
    plan_id: int
    customer_id: int
    vehicle_id: int
    card_id: int | None = None
    start_date: date
    end_date: date
    registered_price: Decimal
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE


class MonthlySubscriptionUpdate(BaseModel):
    plan_id: int | None = None
    customer_id: int | None = None
    vehicle_id: int | None = None
    card_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    registered_price: Decimal | None = None
    status: SubscriptionStatus | None = None


class MonthlySubscriptionResponse(ORMBaseSchema):
    subscription_id: int
    plan_id: int
    customer_id: int
    vehicle_id: int
    card_id: int | None
    start_date: date
    end_date: date
    registered_price: Decimal
    status: SubscriptionStatus
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class ParkingSessionCheckIn(BaseModel):
    card_uid: str
    plate_number: str
    gate_id: int
    image_url: str | None = None


class ParkingSessionCheckOut(BaseModel):
    card_uid: str
    plate_number: str
    gate_id: int
    image_url: str | None = None
    payment_method: PaymentMethod = PaymentMethod.CASH


class ParkingSessionResponse(ORMBaseSchema):
    session_id: int
    session_code: str
    customer_id: int | None
    vehicle_id: int | None
    card_id: int | None
    subscription_id: int | None
    vehicle_type: VehicleType
    entry_gate_id: int
    exit_gate_id: int | None
    entry_time: datetime
    exit_time: datetime | None
    entry_plate_number: str | None
    exit_plate_number: str | None
    entry_plate_image: str | None
    exit_plate_image: str | None
    plate_match_flag: bool
    entry_staff_id: int | None
    exit_staff_id: int | None
    parking_fee: Decimal
    payment_status: PaymentStatus
    session_status: SessionStatus
    note: str | None
    created_at: datetime
    updated_at: datetime


class ParkingSessionActionResponse(BaseModel):
    allow_open_barrier: bool
    message: str
    session: ParkingSessionResponse
    payment: dict | None = None


class PaymentCreate(BaseModel):
    payment_type: str = "single"
    session_id: int | None = None
    subscription_id: int | None = None
    customer_id: int | None = None
    amount: Decimal
    payment_method: PaymentMethod
    status: PaymentRecordStatus = PaymentRecordStatus.PAID
    paid_at: datetime | None = None
    note: str | None = None


class PaymentUpdate(BaseModel):
    payment_type: str | None = None
    session_id: int | None = None
    subscription_id: int | None = None
    customer_id: int | None = None
    amount: Decimal | None = None
    payment_method: PaymentMethod | None = None
    status: PaymentRecordStatus | None = None
    paid_at: datetime | None = None
    note: str | None = None


class PaymentResponse(ORMBaseSchema):
    payment_id: int
    payment_code: str
    payment_type: str
    session_id: int | None
    subscription_id: int | None
    customer_id: int | None
    amount: Decimal
    payment_method: PaymentMethod
    status: PaymentRecordStatus
    paid_at: datetime | None
    created_by: int | None
    note: str | None
    created_at: datetime
    updated_at: datetime


class RevenueItem(BaseModel):
    period: date | str
    total_amount: Decimal


class DeviceCreate(BaseModel):
    lot_id: int | None = None
    zone_id: int | None = None
    gate_id: int | None = None
    device_code: str
    device_name: str
    device_type: DeviceType
    serial_number: str | None = None
    ip_address: str | None = None
    firmware_version: str | None = None
    status: DeviceStatus = DeviceStatus.ONLINE
    installed_at: datetime | None = None
    last_seen_at: datetime | None = None
    note: str | None = None


class DeviceUpdate(BaseModel):
    lot_id: int | None = None
    zone_id: int | None = None
    gate_id: int | None = None
    device_code: str | None = None
    device_name: str | None = None
    device_type: DeviceType | None = None
    serial_number: str | None = None
    ip_address: str | None = None
    firmware_version: str | None = None
    status: DeviceStatus | None = None
    installed_at: datetime | None = None
    last_seen_at: datetime | None = None
    note: str | None = None


class DeviceStatusUpdate(BaseModel):
    status: DeviceStatus


class DeviceResponse(ORMBaseSchema):
    device_id: int
    lot_id: int | None
    zone_id: int | None
    gate_id: int | None
    device_code: str
    device_name: str
    device_type: DeviceType
    serial_number: str | None
    ip_address: str | None
    firmware_version: str | None
    status: DeviceStatus
    installed_at: datetime | None
    last_seen_at: datetime | None
    note: str | None
    created_at: datetime
    updated_at: datetime


class AlertCreate(BaseModel):
    device_id: int | None = None
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str | None = None
    status: AlertStatus = AlertStatus.OPEN


class AlertUpdate(BaseModel):
    severity: AlertSeverity | None = None
    title: str | None = None
    description: str | None = None
    status: AlertStatus | None = None


class AlertResponse(ORMBaseSchema):
    alert_id: int
    device_id: int | None
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str | None
    status: AlertStatus
    detected_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    resolved_by: int | None
    created_at: datetime
    updated_at: datetime


class GasAlertCreate(BaseModel):
    device_id: int
    gas_value: Decimal


class DashboardSummaryResponse(BaseModel):
    total_current_vehicles: int
    total_unresolved_alerts: int
    today_revenue: Decimal
    active_monthly_customers: int
