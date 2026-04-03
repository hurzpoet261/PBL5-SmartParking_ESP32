from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import PaymentStatus, SessionStatus, VehicleType


class ParkingSession(BaseModel):
    __tablename__ = "parking_sessions"
    __table_args__ = (
        Index("ix_parking_sessions_session_status", "session_status"),
        Index("ix_parking_sessions_entry_time", "entry_time"),
    )

    session_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    session_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.customer_id"), nullable=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.vehicle_id"), nullable=True)
    card_id: Mapped[int | None] = mapped_column(ForeignKey("rfid_cards.card_id"), nullable=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("monthly_subscriptions.subscription_id"), nullable=True)
    vehicle_type: Mapped[VehicleType] = mapped_column(
        Enum(VehicleType, values_callable=lambda x: [e.value for e in x], name="vehicle_type_enum", create_type=False),
        nullable=False,
    )
    entry_gate_id: Mapped[int] = mapped_column(ForeignKey("gates.gate_id"), nullable=False)
    exit_gate_id: Mapped[int | None] = mapped_column(ForeignKey("gates.gate_id"), nullable=True)
    entry_time: Mapped[datetime] = mapped_column(nullable=False)
    exit_time: Mapped[datetime | None] = mapped_column(nullable=True)
    entry_plate_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    exit_plate_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    entry_plate_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exit_plate_image: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plate_match_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    entry_staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff_users.user_id"), nullable=True)
    exit_staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff_users.user_id"), nullable=True)
    parking_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, values_callable=lambda x: [e.value for e in x], name="session_payment_status_enum", create_type=False),
        nullable=False,
        default=PaymentStatus.UNPAID,
        server_default=PaymentStatus.UNPAID.value,
    )
    session_status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, values_callable=lambda x: [e.value for e in x], name="session_status_enum", create_type=False),
        nullable=False,
        default=SessionStatus.IN_PROGRESS,
        server_default=SessionStatus.IN_PROGRESS.value,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer = relationship("Customer", back_populates="parking_sessions")
    vehicle = relationship("Vehicle", back_populates="parking_sessions")
    card = relationship("RFIDCard", back_populates="parking_sessions")
    subscription = relationship("MonthlySubscription", back_populates="parking_sessions")
    entry_gate = relationship("Gate", foreign_keys=[entry_gate_id], back_populates="entry_sessions")
    exit_gate = relationship("Gate", foreign_keys=[exit_gate_id], back_populates="exit_sessions")
    entry_staff = relationship("StaffUser", foreign_keys=[entry_staff_id], back_populates="entry_sessions")
    exit_staff = relationship("StaffUser", foreign_keys=[exit_staff_id], back_populates="exit_sessions")
    payments = relationship("Payment", back_populates="session")
