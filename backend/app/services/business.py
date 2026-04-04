from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException, UnauthorizedException
from app.core.security import create_access_token, verify_password
from app.models import (
    Alert,
    Customer,
    Device,
    DeviceLog,
    Gate,
    MonthlyPlan,
    MonthlySubscription,
    ParkingSession,
    Payment,
    RFIDCard,
    StaffUser,
    Vehicle,
)
from app.models.enums import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    CardStatus,
    DeviceStatus,
    GateType,
    LogLevel,
    PaymentMethod,
    PaymentRecordStatus,
    PaymentStatus,
    PaymentType,
    SessionStatus,
    StaffRole,
    SubscriptionStatus,
    UserStatus,
    VehicleType,
)


FEE_BY_VEHICLE_TYPE = {
    VehicleType.MOTORBIKE: Decimal("5000.00"),
    VehicleType.CAR: Decimal("20000.00"),
    VehicleType.BICYCLE: Decimal("3000.00"),
    VehicleType.TRUCK: Decimal("30000.00"),
    VehicleType.OTHER: Decimal("10000.00"),
}

GAS_THRESHOLD = Decimal("50")
GAS_ALERT_COOLDOWN_MINUTES = 5


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_code(prefix: str) -> str:
    return f"{prefix}{utc_now_naive().strftime('%Y%m%d%H%M%S%f')}"


def login_user(db: Session, username: str, password: str) -> tuple[str, StaffUser]:
    user = db.execute(select(StaffUser).where(StaffUser.username == username)).scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise UnauthorizedException("Incorrect username or password")
    if user.status != UserStatus.ACTIVE:
        raise UnauthorizedException("User is inactive")
    token = create_access_token(user.user_id)
    return token, user


def require_admin_role(user: StaffUser) -> None:
    if user.role != StaffRole.ADMIN:
        raise UnauthorizedException("Admin permission required")


def create_customer(db: Session, payload: dict) -> Customer:
    exists = db.execute(
        select(Customer).where(
            or_(Customer.customer_code == payload["customer_code"], Customer.phone == payload.get("phone"))
        )
    ).scalar_one_or_none()
    if exists and exists.customer_code == payload["customer_code"]:
        raise BadRequestException("Customer code already exists")
    customer = Customer(**payload)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def update_model(db: Session, instance, payload: dict):
    try:
        for key, value in payload.items():
            setattr(instance, key, value)
        db.commit()
        db.refresh(instance)
        return instance
    except IntegrityError as exc:
        db.rollback()
        raise BadRequestException("Update failed due to related data or invalid constraint") from exc


def delete_model(db: Session, instance):
    try:
        db.delete(instance)
        db.commit()
        return {"message": "Deleted successfully"}
    except IntegrityError as exc:
        db.rollback()
        raise BadRequestException("Cannot delete this record because it is referenced by other data") from exc


def create_vehicle(db: Session, payload: dict) -> Vehicle:
    exists = db.execute(select(Vehicle).where(Vehicle.plate_number == payload["plate_number"])).scalar_one_or_none()
    if exists:
        raise BadRequestException("Plate number already exists")
    vehicle = Vehicle(**payload)
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def create_rfid_card(db: Session, payload: dict) -> RFIDCard:
    exists = db.execute(select(RFIDCard).where(RFIDCard.card_uid == payload["card_uid"])).scalar_one_or_none()
    if exists:
        raise BadRequestException("Card UID already exists")
    card = RFIDCard(**payload)
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


def create_monthly_plan(db: Session, payload: dict) -> MonthlyPlan:
    plan = MonthlyPlan(**payload)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def create_monthly_subscription(db: Session, payload: dict, created_by: int | None) -> MonthlySubscription:
    payload["created_by"] = created_by
    subscription = MonthlySubscription(**payload)
    db.add(subscription)
    if payload.get("card_id"):
        card = db.get(RFIDCard, payload["card_id"])
        if card:
            card.status = CardStatus.ASSIGNED
    db.commit()
    db.refresh(subscription)
    return subscription


def create_payment(db: Session, payload: dict, created_by: int | None) -> Payment:
    payment = Payment(
        payment_code=generate_code("PAY"),
        payment_type=PaymentType(payload["payment_type"]),
        session_id=payload.get("session_id"),
        subscription_id=payload.get("subscription_id"),
        customer_id=payload.get("customer_id"),
        amount=payload["amount"],
        payment_method=payload["payment_method"],
        status=payload.get("status", PaymentRecordStatus.PAID),
        paid_at=payload.get("paid_at") or utc_now_naive(),
        created_by=created_by,
        note=payload.get("note"),
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def create_device(db: Session, payload: dict) -> Device:
    exists = db.execute(select(Device).where(Device.device_code == payload["device_code"])).scalar_one_or_none()
    if exists:
        raise BadRequestException("Device code already exists")
    device = Device(**payload)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def create_alert(db: Session, payload: dict) -> Alert:
    alert = Alert(
        device_id=payload.get("device_id"),
        alert_type=payload["alert_type"],
        severity=payload["severity"],
        title=payload["title"],
        description=payload.get("description"),
        status=payload.get("status", AlertStatus.OPEN),
        detected_at=utc_now_naive(),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def find_active_subscription(db: Session, vehicle_id: int | None, card_id: int | None):
    today = date.today()
    stmt = select(MonthlySubscription).where(
        MonthlySubscription.status == SubscriptionStatus.ACTIVE,
        MonthlySubscription.start_date <= today,
        MonthlySubscription.end_date >= today,
    )
    if vehicle_id is not None and card_id is not None:
        stmt = stmt.where(
            or_(MonthlySubscription.vehicle_id == vehicle_id, MonthlySubscription.card_id == card_id)
        )
    elif vehicle_id is not None:
        stmt = stmt.where(MonthlySubscription.vehicle_id == vehicle_id)
    elif card_id is not None:
        stmt = stmt.where(MonthlySubscription.card_id == card_id)
    else:
        return None
    return db.execute(stmt).scalars().first()


def check_in_vehicle(db: Session, payload: dict, staff_user: StaffUser) -> dict:
    gate = db.get(Gate, payload["gate_id"])
    if not gate:
        raise NotFoundException("Gate not found")
    if gate.gate_type not in [GateType.ENTRY, GateType.BOTH]:
        raise BadRequestException("This gate cannot be used for check-in")

    card = db.execute(select(RFIDCard).where(RFIDCard.card_uid == payload["card_uid"])).scalar_one_or_none()
    if not card:
        raise NotFoundException("RFID card not found")
    if card.status not in [CardStatus.ASSIGNED, CardStatus.AVAILABLE]:
        raise BadRequestException("RFID card status is not valid for check-in")

    vehicle = card.assigned_vehicle
    customer = card.assigned_customer

    existing_session = db.execute(
        select(ParkingSession).where(
            ParkingSession.session_status == SessionStatus.IN_PROGRESS,
            or_(
                ParkingSession.card_id == card.card_id,
                ParkingSession.vehicle_id == getattr(vehicle, "vehicle_id", None),
            ),
        )
    ).scalars().first()
    if existing_session:
        raise BadRequestException("Card or vehicle already has an active parking session")

    subscription = find_active_subscription(db, getattr(vehicle, "vehicle_id", None), card.card_id)
    payment_status = PaymentStatus.COVERED if subscription else PaymentStatus.UNPAID
    vehicle_type = vehicle.vehicle_type if vehicle else VehicleType.OTHER

    session = ParkingSession(
        session_code=generate_code("PS"),
        customer_id=getattr(customer, "customer_id", None),
        vehicle_id=getattr(vehicle, "vehicle_id", None),
        card_id=card.card_id,
        subscription_id=getattr(subscription, "subscription_id", None),
        vehicle_type=vehicle_type,
        entry_gate_id=payload["gate_id"],
        entry_time=utc_now_naive(),
        entry_plate_number=payload["plate_number"],
        entry_plate_image=payload.get("image_url"),
        plate_match_flag=True,
        entry_staff_id=staff_user.user_id,
        parking_fee=Decimal("0.00"),
        payment_status=payment_status,
        session_status=SessionStatus.IN_PROGRESS,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "allow_open_barrier": True,
        "message": "Check-in successful",
        "session": session,
        "payment": None,
    }


def check_out_vehicle(db: Session, payload: dict, staff_user: StaffUser) -> dict:
    card = db.execute(select(RFIDCard).where(RFIDCard.card_uid == payload["card_uid"])).scalar_one_or_none()
    if not card:
        raise NotFoundException("RFID card not found")

    gate = db.get(Gate, payload["gate_id"])
    if not gate:
        raise NotFoundException("Gate not found")
    if gate.gate_type not in [GateType.EXIT, GateType.BOTH]:
        raise BadRequestException("This gate cannot be used for check-out")

    session = db.execute(
        select(ParkingSession).where(
            ParkingSession.card_id == card.card_id,
            ParkingSession.session_status == SessionStatus.IN_PROGRESS,
        )
    ).scalars().first()
    if not session:
        raise NotFoundException("Active parking session not found")

    session.exit_time = utc_now_naive()
    session.exit_gate_id = payload["gate_id"]
    session.exit_plate_number = payload["plate_number"]
    session.exit_plate_image = payload.get("image_url")
    session.plate_match_flag = (session.entry_plate_number or "").upper() == payload["plate_number"].upper()
    session.exit_staff_id = staff_user.user_id

    payment_data = None
    subscription = find_active_subscription(db, session.vehicle_id, session.card_id)
    if subscription:
        session.payment_status = PaymentStatus.COVERED
        session.subscription_id = subscription.subscription_id
        session.parking_fee = Decimal("0.00")
    else:
        amount = FEE_BY_VEHICLE_TYPE.get(session.vehicle_type, FEE_BY_VEHICLE_TYPE[VehicleType.OTHER])
        session.parking_fee = amount
        session.payment_status = PaymentStatus.PAID
        payment = Payment(
            payment_code=generate_code("PAY"),
            payment_type=PaymentType.SINGLE,
            session_id=session.session_id,
            subscription_id=None,
            customer_id=session.customer_id,
            amount=amount,
            payment_method=payload.get("payment_method", PaymentMethod.CASH),
            status=PaymentRecordStatus.PAID,
            paid_at=utc_now_naive(),
            created_by=staff_user.user_id,
            note="Parking fee collected at check-out",
        )
        db.add(payment)
        db.flush()
        payment_data = {
            "payment_id": payment.payment_id,
            "payment_code": payment.payment_code,
            "amount": payment.amount,
            "payment_type": payment.payment_type,
            "status": payment.status,
        }

    if not session.plate_match_flag:
        recent_plate_alert = db.execute(
            select(Alert).where(
                Alert.alert_type == AlertType.PLATE_MISMATCH,
                Alert.status == AlertStatus.OPEN,
                Alert.detected_at >= utc_now_naive() - timedelta(minutes=5),
            )
        ).scalars().first()
        if not recent_plate_alert:
            db.add(
                Alert(
                    device_id=None,
                    alert_type=AlertType.PLATE_MISMATCH,
                    severity=AlertSeverity.MEDIUM,
                    title="Plate mismatch detected",
                    description=f"Entry plate {session.entry_plate_number} differs from exit plate {payload['plate_number']}",
                    status=AlertStatus.OPEN,
                    detected_at=utc_now_naive(),
                    resolved_by=None,
                )
            )

    session.session_status = SessionStatus.COMPLETED
    db.commit()
    db.refresh(session)

    return {
        "allow_open_barrier": True,
        "message": "Check-out successful",
        "session": session,
        "payment": payment_data,
    }


def process_gas_alert(db: Session, device_id: int, gas_value: Decimal) -> dict:
    device = db.get(Device, device_id)
    if not device:
        raise NotFoundException("Device not found")

    log = DeviceLog(
        device_id=device_id,
        log_type="gas_reading",
        log_level=LogLevel.WARNING if gas_value > GAS_THRESHOLD else LogLevel.INFO,
        message=f"Gas sensor reading received: {gas_value}",
        sensor_value=gas_value,
        raw_data={"gas_value": float(gas_value), "threshold": float(GAS_THRESHOLD)},
    )
    db.add(log)

    alert_created = False
    if gas_value > GAS_THRESHOLD:
        cooldown_time = utc_now_naive() - timedelta(minutes=GAS_ALERT_COOLDOWN_MINUTES)
        recent_alert = db.execute(
            select(Alert).where(
                Alert.device_id == device_id,
                Alert.alert_type == AlertType.GAS,
                Alert.status == AlertStatus.OPEN,
                Alert.detected_at >= cooldown_time,
            )
        ).scalars().first()
        if not recent_alert:
            db.add(
                Alert(
                    device_id=device_id,
                    alert_type=AlertType.GAS,
                    severity=AlertSeverity.HIGH,
                    title="Gas concentration above threshold",
                    description=f"Gas value {gas_value} exceeded threshold {GAS_THRESHOLD}",
                    status=AlertStatus.OPEN,
                    detected_at=utc_now_naive(),
                    resolved_by=None,
                )
            )
            alert_created = True

    db.commit()
    return {
        "device_id": device_id,
        "gas_value": gas_value,
        "threshold": GAS_THRESHOLD,
        "alert_created": alert_created,
        "message": "Gas reading processed successfully",
    }


def get_dashboard_summary(db: Session) -> dict:
    today = date.today()
    total_current_vehicles = db.execute(
        select(func.count(ParkingSession.session_id)).where(ParkingSession.session_status == SessionStatus.IN_PROGRESS)
    ).scalar_one()
    total_unresolved_alerts = db.execute(
        select(func.count(Alert.alert_id)).where(Alert.status == AlertStatus.OPEN)
    ).scalar_one()
    today_revenue = db.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(func.date(Payment.paid_at) == today)
    ).scalar_one()
    active_monthly_customers = db.execute(
        select(func.count(func.distinct(MonthlySubscription.customer_id))).where(
            MonthlySubscription.status == SubscriptionStatus.ACTIVE,
            MonthlySubscription.start_date <= today,
            MonthlySubscription.end_date >= today,
        )
    ).scalar_one()
    return {
        "total_current_vehicles": total_current_vehicles,
        "total_unresolved_alerts": total_unresolved_alerts,
        "today_revenue": today_revenue,
        "active_monthly_customers": active_monthly_customers,
    }


def get_revenue_daily(db: Session):
    rows = db.execute(
        select(func.date(Payment.paid_at).label("period"), func.coalesce(func.sum(Payment.amount), 0).label("total_amount"))
        .where(Payment.paid_at.is_not(None))
        .group_by(func.date(Payment.paid_at))
        .order_by(func.date(Payment.paid_at).desc())
    ).all()
    return [{"period": row.period, "total_amount": row.total_amount} for row in rows]


def get_revenue_monthly(db: Session):
    rows = db.execute(
        select(
            func.to_char(Payment.paid_at, "YYYY-MM").label("period"),
            func.coalesce(func.sum(Payment.amount), 0).label("total_amount"),
        )
        .where(Payment.paid_at.is_not(None))
        .group_by(func.to_char(Payment.paid_at, "YYYY-MM"))
        .order_by(func.to_char(Payment.paid_at, "YYYY-MM").desc())
    ).all()
    return [{"period": row.period, "total_amount": row.total_amount} for row in rows]
