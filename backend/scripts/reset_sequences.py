from sqlalchemy import text

from app.core.database import SessionLocal


TABLES = [
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


def reset_sequences() -> None:
    db = SessionLocal()
    try:
        for table_name, pk_column in TABLES:
            sql = text(
                f"SELECT setval(pg_get_serial_sequence('{table_name}', '{pk_column}'), COALESCE((SELECT MAX({pk_column}) FROM {table_name}), 1), true)"
            )
            db.execute(sql)
        db.commit()
        print("Sequences reset successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    reset_sequences()
