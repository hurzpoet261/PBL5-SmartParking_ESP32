from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    Alert,
    Customer,
    Device,
    DeviceLog,
    Gate,
    MonthlyPlan,
    MonthlySubscription,
    ParkingLot,
    ParkingSession,
    ParkingZone,
    Payment,
    RFIDCard,
    StaffUser,
    SystemLog,
    Vehicle,
)
from app.models.enums import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    CardStatus,
    CardType,
    CustomerType,
    DeviceStatus,
    DeviceType,
    GateStatus,
    GateType,
    LogLevel,
    LotStatus,
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


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_or_create(session, model, defaults=None, **kwargs):
    instance = session.execute(select(model).filter_by(**kwargs)).scalar_one_or_none()
    if instance:
        return instance, False

    params = {**kwargs}
    if defaults:
        params.update(defaults)
    instance = model(**params)
    session.add(instance)
    session.flush()
    return instance, True


def reset_sequences(db) -> None:
    tables = [
        ("parking_lots", "lot_id"),
        ("parking_zones", "zone_id"),
        ("gates", "gate_id"),
        ("staff_users", "user_id"),
        ("customers", "customer_id"),
        ("vehicles", "vehicle_id"),
        ("rfid_cards", "card_id"),
        ("monthly_plans", "plan_id"),
        ("monthly_subscriptions", "subscription_id"),
        ("parking_sessions", "session_id"),
        ("payments", "payment_id"),
        ("devices", "device_id"),
        ("alerts", "alert_id"),
        ("device_logs", "log_id"),
        ("system_logs", "system_log_id"),
    ]
    from sqlalchemy import text

    for table_name, pk_column in tables:
        db.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence('{table_name}', '{pk_column}'), COALESCE((SELECT MAX({pk_column}) FROM {table_name}), 1), true)"
            )
        )



def seed() -> None:
    db = SessionLocal()
    try:
        lot, _ = get_or_create(
            db,
            ParkingLot,
            lot_code="LOT001",
            defaults={
                "lot_id": 1,
                "lot_name": "Smart Parking Central",
                "address": "123 Nguyen Van Linh, District 7, HCMC",
                "total_capacity": 120,
                "status": LotStatus.ACTIVE,
            },
        )

        zone_a, _ = get_or_create(
            db,
            ParkingZone,
            zone_code="ZONE-MB",
            defaults={
                "zone_id": 1,
                "lot_id": lot.lot_id,
                "zone_name": "Motorbike Zone",
                "vehicle_type": VehicleType.MOTORBIKE,
                "capacity": 80,
                "status": LotStatus.ACTIVE,
            },
        )
        zone_b, _ = get_or_create(
            db,
            ParkingZone,
            zone_code="ZONE-CAR",
            defaults={
                "zone_id": 2,
                "lot_id": lot.lot_id,
                "zone_name": "Car Zone",
                "vehicle_type": VehicleType.CAR,
                "capacity": 40,
                "status": LotStatus.ACTIVE,
            },
        )

        entry_gate, _ = get_or_create(
            db,
            Gate,
            gate_code="GATE-IN-01",
            defaults={
                "gate_id": 1,
                "lot_id": lot.lot_id,
                "zone_id": zone_a.zone_id,
                "gate_name": "Entry Gate 01",
                "gate_type": GateType.ENTRY,
                "status": GateStatus.ACTIVE,
            },
        )
        exit_gate, _ = get_or_create(
            db,
            Gate,
            gate_code="GATE-OUT-01",
            defaults={
                "gate_id": 2,
                "lot_id": lot.lot_id,
                "zone_id": zone_a.zone_id,
                "gate_name": "Exit Gate 01",
                "gate_type": GateType.EXIT,
                "status": GateStatus.ACTIVE,
            },
        )

        admin_user, _ = get_or_create(
            db,
            StaffUser,
            username="admin",
            defaults={
                "user_id": 1,
                "lot_id": lot.lot_id,
                "full_name": "System Admin",
                "password_hash": hash_password("admin123"),
                "role": StaffRole.ADMIN,
                "phone": "0900000001",
                "email": "admin@smartparking.local",
                "status": UserStatus.ACTIVE,
            },
        )
        staff_user, _ = get_or_create(
            db,
            StaffUser,
            username="staff01",
            defaults={
                "user_id": 2,
                "lot_id": lot.lot_id,
                "full_name": "Front Gate Staff",
                "password_hash": hash_password("staff123"),
                "role": StaffRole.STAFF,
                "phone": "0900000002",
                "email": "staff01@smartparking.local",
                "status": UserStatus.ACTIVE,
            },
        )

        customer_a, _ = get_or_create(
            db,
            Customer,
            customer_code="CUS001",
            defaults={
                "customer_id": 1,
                "full_name": "Nguyen Van A",
                "phone": "0911111111",
                "email": "customer.a@example.com",
                "address": "Thu Duc City",
                "customer_type": CustomerType.MONTHLY,
                "status": UserStatus.ACTIVE,
            },
        )
        customer_b, _ = get_or_create(
            db,
            Customer,
            customer_code="CUS002",
            defaults={
                "customer_id": 2,
                "full_name": "Tran Thi B",
                "phone": "0922222222",
                "email": "customer.b@example.com",
                "address": "District 7",
                "customer_type": CustomerType.WALK_IN,
                "status": UserStatus.ACTIVE,
            },
        )

        vehicle_a, _ = get_or_create(
            db,
            Vehicle,
            plate_number="59A1-12345",
            defaults={
                "vehicle_id": 1,
                "customer_id": customer_a.customer_id,
                "vehicle_type": VehicleType.MOTORBIKE,
                "brand": "Honda",
                "model": "Vision",
                "color": "Red",
                "status": LotStatus.ACTIVE,
            },
        )
        vehicle_b, _ = get_or_create(
            db,
            Vehicle,
            plate_number="51H-88888",
            defaults={
                "vehicle_id": 2,
                "customer_id": customer_b.customer_id,
                "vehicle_type": VehicleType.CAR,
                "brand": "Toyota",
                "model": "Vios",
                "color": "White",
                "status": LotStatus.ACTIVE,
            },
        )

        card_a, _ = get_or_create(
            db,
            RFIDCard,
            card_uid="UID0001",
            defaults={
                "card_id": 1,
                "card_code": "CARD001",
                "card_type": CardType.MONTHLY,
                "assigned_customer_id": customer_a.customer_id,
                "assigned_vehicle_id": vehicle_a.vehicle_id,
                "issued_at": utc_now(),
                "expired_at": utc_now() + timedelta(days=365),
                "status": CardStatus.ASSIGNED,
                "note": "Monthly subscriber card",
            },
        )
        card_b, _ = get_or_create(
            db,
            RFIDCard,
            card_uid="UID0002",
            defaults={
                "card_id": 2,
                "card_code": "CARD002",
                "card_type": CardType.GUEST,
                "assigned_customer_id": None,
                "assigned_vehicle_id": None,
                "issued_at": utc_now(),
                "expired_at": None,
                "status": CardStatus.AVAILABLE,
                "note": "Guest card at entry gate",
            },
        )

        plan_a, _ = get_or_create(
            db,
            MonthlyPlan,
            plan_name="Motorbike Monthly Plan",
            defaults={
                "plan_id": 1,
                "vehicle_type": VehicleType.MOTORBIKE,
                "duration_months": 1,
                "price": Decimal("150000.00"),
                "description": "Monthly parking plan for motorbikes",
                "status": LotStatus.ACTIVE,
            },
        )
        plan_b, _ = get_or_create(
            db,
            MonthlyPlan,
            plan_name="Car Monthly Plan",
            defaults={
                "plan_id": 2,
                "vehicle_type": VehicleType.CAR,
                "duration_months": 1,
                "price": Decimal("1200000.00"),
                "description": "Monthly parking plan for cars",
                "status": LotStatus.ACTIVE,
            },
        )

        subscription, _ = get_or_create(
            db,
            MonthlySubscription,
            subscription_id=1,
            defaults={
                "plan_id": plan_a.plan_id,
                "customer_id": customer_a.customer_id,
                "vehicle_id": vehicle_a.vehicle_id,
                "card_id": card_a.card_id,
                "start_date": date.today(),
                "end_date": date.today() + timedelta(days=30),
                "registered_price": Decimal("150000.00"),
                "status": SubscriptionStatus.ACTIVE,
                "created_by": admin_user.user_id,
            },
        )

        session_1, _ = get_or_create(
            db,
            ParkingSession,
            session_code="PS0001",
            defaults={
                "session_id": 1,
                "customer_id": customer_a.customer_id,
                "vehicle_id": vehicle_a.vehicle_id,
                "card_id": card_a.card_id,
                "subscription_id": subscription.subscription_id,
                "vehicle_type": VehicleType.MOTORBIKE,
                "entry_gate_id": entry_gate.gate_id,
                "exit_gate_id": exit_gate.gate_id,
                "entry_time": utc_now() - timedelta(hours=2),
                "exit_time": utc_now() - timedelta(hours=1),
                "entry_plate_number": "59A1-12345",
                "exit_plate_number": "59A1-12345",
                "entry_plate_image": "images/entry/session1.jpg",
                "exit_plate_image": "images/exit/session1.jpg",
                "plate_match_flag": True,
                "entry_staff_id": staff_user.user_id,
                "exit_staff_id": staff_user.user_id,
                "parking_fee": Decimal("0.00"),
                "payment_status": PaymentStatus.COVERED,
                "session_status": SessionStatus.COMPLETED,
                "note": "Monthly subscription vehicle",
            },
        )
        session_2, _ = get_or_create(
            db,
            ParkingSession,
            session_code="PS0002",
            defaults={
                "session_id": 2,
                "customer_id": customer_b.customer_id,
                "vehicle_id": vehicle_b.vehicle_id,
                "card_id": card_b.card_id,
                "subscription_id": None,
                "vehicle_type": VehicleType.CAR,
                "entry_gate_id": entry_gate.gate_id,
                "exit_gate_id": None,
                "entry_time": utc_now() - timedelta(minutes=30),
                "exit_time": None,
                "entry_plate_number": "51H-88888",
                "exit_plate_number": None,
                "entry_plate_image": "images/entry/session2.jpg",
                "exit_plate_image": None,
                "plate_match_flag": True,
                "entry_staff_id": staff_user.user_id,
                "exit_staff_id": None,
                "parking_fee": Decimal("0.00"),
                "payment_status": PaymentStatus.UNPAID,
                "session_status": SessionStatus.IN_PROGRESS,
                "note": "Walk-in car currently inside parking lot",
            },
        )

        get_or_create(
            db,
            Payment,
            payment_code="PAY0001",
            defaults={
                "payment_id": 1,
                "payment_type": PaymentType.SINGLE,
                "session_id": session_1.session_id,
                "subscription_id": None,
                "customer_id": customer_a.customer_id,
                "amount": Decimal("0.00"),
                "payment_method": PaymentMethod.CASH,
                "status": PaymentRecordStatus.PAID,
                "paid_at": utc_now() - timedelta(hours=1),
                "created_by": staff_user.user_id,
                "note": "Covered by monthly subscription",
            },
        )

        device_1, _ = get_or_create(
            db,
            Device,
            device_code="DEV-RFID-01",
            defaults={
                "device_id": 1,
                "lot_id": lot.lot_id,
                "zone_id": zone_a.zone_id,
                "gate_id": entry_gate.gate_id,
                "device_name": "RFID Reader Entry",
                "device_type": DeviceType.RFID_READER,
                "serial_number": "RFID-ENTRY-0001",
                "ip_address": "192.168.1.10",
                "firmware_version": "1.0.0",
                "status": DeviceStatus.ONLINE,
                "installed_at": utc_now() - timedelta(days=30),
                "last_seen_at": utc_now(),
                "note": "Installed at entry gate",
            },
        )
        get_or_create(
            db,
            Device,
            device_code="DEV-CAM-01",
            defaults={
                "device_id": 2,
                "lot_id": lot.lot_id,
                "zone_id": zone_a.zone_id,
                "gate_id": entry_gate.gate_id,
                "device_name": "ANPR Camera Entry",
                "device_type": DeviceType.CAMERA,
                "serial_number": "CAM-ENTRY-0001",
                "ip_address": "192.168.1.11",
                "firmware_version": "2.1.0",
                "status": DeviceStatus.ONLINE,
                "installed_at": utc_now() - timedelta(days=30),
                "last_seen_at": utc_now(),
                "note": "License plate recognition camera",
            },
        )
        device_3, _ = get_or_create(
            db,
            Device,
            device_code="DEV-GAS-01",
            defaults={
                "device_id": 3,
                "lot_id": lot.lot_id,
                "zone_id": zone_b.zone_id,
                "gate_id": None,
                "device_name": "Gas Sensor Basement",
                "device_type": DeviceType.GAS_SENSOR,
                "serial_number": "GAS-0001",
                "ip_address": "192.168.1.20",
                "firmware_version": "1.5.2",
                "status": DeviceStatus.ONLINE,
                "installed_at": utc_now() - timedelta(days=20),
                "last_seen_at": utc_now(),
                "note": "Monitors CO and flammable gas",
            },
        )

        get_or_create(
            db,
            Alert,
            alert_id=1,
            defaults={
                "device_id": device_3.device_id,
                "alert_type": AlertType.GAS,
                "severity": AlertSeverity.HIGH,
                "title": "Gas concentration above threshold",
                "description": "Gas sensor detected abnormal concentration in car zone.",
                "status": AlertStatus.OPEN,
                "detected_at": utc_now() - timedelta(minutes=10),
                "acknowledged_at": None,
                "resolved_at": None,
                "resolved_by": None,
            },
        )

        get_or_create(
            db,
            DeviceLog,
            log_id=1,
            defaults={
                "device_id": device_3.device_id,
                "log_type": "gas_reading",
                "log_level": LogLevel.WARNING,
                "message": "Gas value exceeded safe threshold",
                "sensor_value": Decimal("78.50"),
                "raw_data": {"gas_ppm": 78.5, "threshold": 60, "unit": "ppm"},
            },
        )
        get_or_create(
            db,
            DeviceLog,
            log_id=2,
            defaults={
                "device_id": device_1.device_id,
                "log_type": "rfid_scan",
                "log_level": LogLevel.INFO,
                "message": "RFID card scanned successfully at entry gate",
                "sensor_value": None,
                "raw_data": {"card_uid": "UID0002", "gate": "GATE-IN-01", "result": "success"},
            },
        )

        get_or_create(
            db,
            SystemLog,
            system_log_id=1,
            defaults={
                "user_id": admin_user.user_id,
                "action": "seed_data",
                "module_name": "system",
                "record_id": "initial-seed",
                "description": "Initial Phase 2 seed data inserted",
                "ip_address": "127.0.0.1",
            },
        )

        db.commit()
        reset_sequences(db)
        db.commit()
        print("Seed data inserted successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
