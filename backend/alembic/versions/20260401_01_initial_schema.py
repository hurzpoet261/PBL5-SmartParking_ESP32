"""initial schema

Revision ID: 20260401_01
Revises:
Create Date: 2026-04-01 21:40:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260401_01"
down_revision = None
branch_labels = None
depends_on = None


# =========================
# PostgreSQL ENUM types
# =========================
lot_status_enum = postgresql.ENUM(
    "active", "inactive",
    name="lot_status_enum",
    create_type=False,
)

vehicle_type_enum = postgresql.ENUM(
    "motorbike", "car", "bicycle", "truck", "other",
    name="vehicle_type_enum",
    create_type=False,
)

zone_status_enum = postgresql.ENUM(
    "active", "inactive",
    name="zone_status_enum",
    create_type=False,
)

gate_type_enum = postgresql.ENUM(
    "entry", "exit", "both",
    name="gate_type_enum",
    create_type=False,
)

gate_status_enum = postgresql.ENUM(
    "active", "inactive", "maintenance",
    name="gate_status_enum",
    create_type=False,
)

staff_role_enum = postgresql.ENUM(
    "admin", "staff",
    name="staff_role_enum",
    create_type=False,
)

user_status_enum = postgresql.ENUM(
    "active", "inactive",
    name="user_status_enum",
    create_type=False,
)

customer_type_enum = postgresql.ENUM(
    "walk_in", "monthly",
    name="customer_type_enum",
    create_type=False,
)

customer_status_enum = postgresql.ENUM(
    "active", "inactive",
    name="customer_status_enum",
    create_type=False,
)

vehicle_status_enum = postgresql.ENUM(
    "active", "inactive",
    name="vehicle_status_enum",
    create_type=False,
)

card_type_enum = postgresql.ENUM(
    "guest", "monthly", "staff",
    name="card_type_enum",
    create_type=False,
)

card_status_enum = postgresql.ENUM(
    "available", "assigned", "lost", "blocked", "inactive",
    name="card_status_enum",
    create_type=False,
)

plan_status_enum = postgresql.ENUM(
    "active", "inactive",
    name="plan_status_enum",
    create_type=False,
)

subscription_status_enum = postgresql.ENUM(
    "active", "expired", "cancelled",
    name="subscription_status_enum",
    create_type=False,
)

session_payment_status_enum = postgresql.ENUM(
    "unpaid", "paid", "covered",
    name="session_payment_status_enum",
    create_type=False,
)

session_status_enum = postgresql.ENUM(
    "in_progress", "completed", "lost_card", "abnormal",
    name="session_status_enum",
    create_type=False,
)

payment_type_enum = postgresql.ENUM(
    "single", "monthly",
    name="payment_type_enum",
    create_type=False,
)

payment_method_enum = postgresql.ENUM(
    "cash", "bank_transfer", "e_wallet",
    name="payment_method_enum",
    create_type=False,
)

payment_record_status_enum = postgresql.ENUM(
    "pending", "paid", "failed", "refunded",
    name="payment_record_status_enum",
    create_type=False,
)

device_type_enum = postgresql.ENUM(
    "rfid_reader", "camera", "barrier", "gas_sensor", "esp32_controller", "display", "other",
    name="device_type_enum",
    create_type=False,
)

device_status_enum = postgresql.ENUM(
    "online", "offline", "maintenance", "error",
    name="device_status_enum",
    create_type=False,
)

alert_type_enum = postgresql.ENUM(
    "gas", "device_offline", "plate_mismatch", "barrier_error", "unauthorized_access", "other",
    name="alert_type_enum",
    create_type=False,
)

alert_severity_enum = postgresql.ENUM(
    "low", "medium", "high", "critical",
    name="alert_severity_enum",
    create_type=False,
)

alert_status_enum = postgresql.ENUM(
    "open", "acknowledged", "resolved",
    name="alert_status_enum",
    create_type=False,
)

log_level_enum = postgresql.ENUM(
    "info", "warning", "error",
    name="log_level_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    enums = [
        lot_status_enum,
        vehicle_type_enum,
        zone_status_enum,
        gate_type_enum,
        gate_status_enum,
        staff_role_enum,
        user_status_enum,
        customer_type_enum,
        customer_status_enum,
        vehicle_status_enum,
        card_type_enum,
        card_status_enum,
        plan_status_enum,
        subscription_status_enum,
        session_payment_status_enum,
        session_status_enum,
        payment_type_enum,
        payment_method_enum,
        payment_record_status_enum,
        device_type_enum,
        device_status_enum,
        alert_type_enum,
        alert_severity_enum,
        alert_status_enum,
        log_level_enum,
    ]

    for enum in enums:
        enum.create(bind, checkfirst=True)

    op.create_table(
        "parking_lots",
        sa.Column("lot_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("lot_code", sa.String(length=20), nullable=False, unique=True),
        sa.Column("lot_name", sa.String(length=100), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("total_capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", lot_status_enum, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "parking_zones",
        sa.Column("zone_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("lot_id", sa.BigInteger(), sa.ForeignKey("parking_lots.lot_id"), nullable=False),
        sa.Column("zone_code", sa.String(length=20), nullable=False, unique=True),
        sa.Column("zone_name", sa.String(length=100), nullable=False),
        sa.Column("vehicle_type", vehicle_type_enum, nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", zone_status_enum, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "gates",
        sa.Column("gate_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("lot_id", sa.BigInteger(), sa.ForeignKey("parking_lots.lot_id"), nullable=False),
        sa.Column("zone_id", sa.BigInteger(), sa.ForeignKey("parking_zones.zone_id"), nullable=True),
        sa.Column("gate_code", sa.String(length=20), nullable=False, unique=True),
        sa.Column("gate_name", sa.String(length=100), nullable=False),
        sa.Column("gate_type", gate_type_enum, nullable=False),
        sa.Column("status", gate_status_enum, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "staff_users",
        sa.Column("user_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("lot_id", sa.BigInteger(), sa.ForeignKey("parking_lots.lot_id"), nullable=True),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", staff_role_enum, nullable=False, server_default="staff"),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True, unique=True),
        sa.Column("status", user_status_enum, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "customers",
        sa.Column("customer_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("customer_code", sa.String(length=20), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("customer_type", customer_type_enum, nullable=False, server_default="walk_in"),
        sa.Column("status", customer_status_enum, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "vehicles",
        sa.Column("vehicle_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("customer_id", sa.BigInteger(), sa.ForeignKey("customers.customer_id"), nullable=True),
        sa.Column("plate_number", sa.String(length=20), nullable=False, unique=True),
        sa.Column("vehicle_type", vehicle_type_enum, nullable=False),
        sa.Column("brand", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=50), nullable=True),
        sa.Column("color", sa.String(length=30), nullable=True),
        sa.Column("status", vehicle_status_enum, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_vehicles_plate_number", "vehicles", ["plate_number"])

    op.create_table(
        "rfid_cards",
        sa.Column("card_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("card_uid", sa.String(length=50), nullable=False, unique=True),
        sa.Column("card_code", sa.String(length=20), nullable=True, unique=True),
        sa.Column("card_type", card_type_enum, nullable=False),
        sa.Column("assigned_customer_id", sa.BigInteger(), sa.ForeignKey("customers.customer_id"), nullable=True),
        sa.Column("assigned_vehicle_id", sa.BigInteger(), sa.ForeignKey("vehicles.vehicle_id"), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("status", card_status_enum, nullable=False, server_default="available"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_rfid_cards_card_uid", "rfid_cards", ["card_uid"])

    op.create_table(
        "monthly_plans",
        sa.Column("plan_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("plan_name", sa.String(length=100), nullable=False),
        sa.Column("vehicle_type", vehicle_type_enum, nullable=False),
        sa.Column("duration_months", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", plan_status_enum, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "monthly_subscriptions",
        sa.Column("subscription_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("plan_id", sa.BigInteger(), sa.ForeignKey("monthly_plans.plan_id"), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), sa.ForeignKey("customers.customer_id"), nullable=False),
        sa.Column("vehicle_id", sa.BigInteger(), sa.ForeignKey("vehicles.vehicle_id"), nullable=False),
        sa.Column("card_id", sa.BigInteger(), sa.ForeignKey("rfid_cards.card_id"), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("registered_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", subscription_status_enum, nullable=False, server_default="active"),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("staff_users.user_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_monthly_subscriptions_end_date", "monthly_subscriptions", ["end_date"])

    op.create_table(
        "parking_sessions",
        sa.Column("session_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("session_code", sa.String(length=30), nullable=False, unique=True),
        sa.Column("customer_id", sa.BigInteger(), sa.ForeignKey("customers.customer_id"), nullable=True),
        sa.Column("vehicle_id", sa.BigInteger(), sa.ForeignKey("vehicles.vehicle_id"), nullable=True),
        sa.Column("card_id", sa.BigInteger(), sa.ForeignKey("rfid_cards.card_id"), nullable=True),
        sa.Column("subscription_id", sa.BigInteger(), sa.ForeignKey("monthly_subscriptions.subscription_id"), nullable=True),
        sa.Column("vehicle_type", vehicle_type_enum, nullable=False),
        sa.Column("entry_gate_id", sa.BigInteger(), sa.ForeignKey("gates.gate_id"), nullable=False),
        sa.Column("exit_gate_id", sa.BigInteger(), sa.ForeignKey("gates.gate_id"), nullable=True),
        sa.Column("entry_time", sa.DateTime(timezone=False), nullable=False),
        sa.Column("exit_time", sa.DateTime(timezone=False), nullable=True),
        sa.Column("entry_plate_number", sa.String(length=20), nullable=True),
        sa.Column("exit_plate_number", sa.String(length=20), nullable=True),
        sa.Column("entry_plate_image", sa.String(length=255), nullable=True),
        sa.Column("exit_plate_image", sa.String(length=255), nullable=True),
        sa.Column("plate_match_flag", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("entry_staff_id", sa.BigInteger(), sa.ForeignKey("staff_users.user_id"), nullable=True),
        sa.Column("exit_staff_id", sa.BigInteger(), sa.ForeignKey("staff_users.user_id"), nullable=True),
        sa.Column("parking_fee", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("payment_status", session_payment_status_enum, nullable=False, server_default="unpaid"),
        sa.Column("session_status", session_status_enum, nullable=False, server_default="in_progress"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_parking_sessions_session_status", "parking_sessions", ["session_status"])
    op.create_index("ix_parking_sessions_entry_time", "parking_sessions", ["entry_time"])

    op.create_table(
        "payments",
        sa.Column("payment_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("payment_code", sa.String(length=30), nullable=False, unique=True),
        sa.Column("payment_type", payment_type_enum, nullable=False),
        sa.Column("session_id", sa.BigInteger(), sa.ForeignKey("parking_sessions.session_id"), nullable=True),
        sa.Column("subscription_id", sa.BigInteger(), sa.ForeignKey("monthly_subscriptions.subscription_id"), nullable=True),
        sa.Column("customer_id", sa.BigInteger(), sa.ForeignKey("customers.customer_id"), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_method", payment_method_enum, nullable=False),
        sa.Column("status", payment_record_status_enum, nullable=False, server_default="pending"),
        sa.Column("paid_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("staff_users.user_id"), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_payments_paid_at", "payments", ["paid_at"])

    op.create_table(
        "devices",
        sa.Column("device_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("lot_id", sa.BigInteger(), sa.ForeignKey("parking_lots.lot_id"), nullable=True),
        sa.Column("zone_id", sa.BigInteger(), sa.ForeignKey("parking_zones.zone_id"), nullable=True),
        sa.Column("gate_id", sa.BigInteger(), sa.ForeignKey("gates.gate_id"), nullable=True),
        sa.Column("device_code", sa.String(length=30), nullable=False, unique=True),
        sa.Column("device_name", sa.String(length=100), nullable=False),
        sa.Column("device_type", device_type_enum, nullable=False),
        sa.Column("serial_number", sa.String(length=100), nullable=True, unique=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("firmware_version", sa.String(length=50), nullable=True),
        sa.Column("status", device_status_enum, nullable=False, server_default="online"),
        sa.Column("installed_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_devices_status", "devices", ["status"])

    op.create_table(
        "alerts",
        sa.Column("alert_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("device_id", sa.BigInteger(), sa.ForeignKey("devices.device_id"), nullable=True),
        sa.Column("alert_type", alert_type_enum, nullable=False),
        sa.Column("severity", alert_severity_enum, nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", alert_status_enum, nullable=False, server_default="open"),
        sa.Column("detected_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("now()")),
        sa.Column("acknowledged_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("resolved_by", sa.BigInteger(), sa.ForeignKey("staff_users.user_id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_alerts_status", "alerts", ["status"])

    op.create_table(
        "device_logs",
        sa.Column("log_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("device_id", sa.BigInteger(), sa.ForeignKey("devices.device_id"), nullable=False),
        sa.Column("log_type", sa.String(length=50), nullable=False),
        sa.Column("log_level", log_level_enum, nullable=False, server_default="info"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("sensor_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "system_logs",
        sa.Column("system_log_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("staff_users.user_id"), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("module_name", sa.String(length=100), nullable=False),
        sa.Column("record_id", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_table("system_logs")
    op.drop_table("device_logs")
    op.drop_index("ix_alerts_status", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_devices_status", table_name="devices")
    op.drop_table("devices")
    op.drop_index("ix_payments_paid_at", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_parking_sessions_entry_time", table_name="parking_sessions")
    op.drop_index("ix_parking_sessions_session_status", table_name="parking_sessions")
    op.drop_table("parking_sessions")
    op.drop_index("ix_monthly_subscriptions_end_date", table_name="monthly_subscriptions")
    op.drop_table("monthly_subscriptions")
    op.drop_table("monthly_plans")
    op.drop_index("ix_rfid_cards_card_uid", table_name="rfid_cards")
    op.drop_table("rfid_cards")
    op.drop_index("ix_vehicles_plate_number", table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_table("customers")
    op.drop_table("staff_users")
    op.drop_table("gates")
    op.drop_table("parking_zones")
    op.drop_table("parking_lots")

    enums = [
        log_level_enum,
        alert_status_enum,
        alert_severity_enum,
        alert_type_enum,
        device_status_enum,
        device_type_enum,
        payment_record_status_enum,
        payment_method_enum,
        payment_type_enum,
        session_status_enum,
        session_payment_status_enum,
        subscription_status_enum,
        plan_status_enum,
        card_status_enum,
        card_type_enum,
        vehicle_status_enum,
        customer_status_enum,
        customer_type_enum,
        user_status_enum,
        staff_role_enum,
        gate_status_enum,
        gate_type_enum,
        zone_status_enum,
        vehicle_type_enum,
        lot_status_enum,
    ]

    for enum in enums:
        enum.drop(bind, checkfirst=True)