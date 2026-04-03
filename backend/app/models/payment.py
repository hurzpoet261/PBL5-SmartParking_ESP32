from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import PaymentMethod, PaymentRecordStatus, PaymentType


class Payment(BaseModel):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_paid_at", "paid_at"),
    )

    payment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    payment_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    payment_type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType, values_callable=lambda x: [e.value for e in x], name="payment_type_enum", create_type=False),
        nullable=False,
    )
    session_id: Mapped[int | None] = mapped_column(ForeignKey("parking_sessions.session_id"), nullable=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("monthly_subscriptions.subscription_id"), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.customer_id"), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, values_callable=lambda x: [e.value for e in x], name="payment_method_enum", create_type=False),
        nullable=False,
    )
    status: Mapped[PaymentRecordStatus] = mapped_column(
        Enum(PaymentRecordStatus, values_callable=lambda x: [e.value for e in x], name="payment_record_status_enum", create_type=False),
        nullable=False,
        default=PaymentRecordStatus.PENDING,
        server_default=PaymentRecordStatus.PENDING.value,
    )
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("staff_users.user_id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    session = relationship("ParkingSession", back_populates="payments")
    subscription = relationship("MonthlySubscription", back_populates="payments")
    customer = relationship("Customer", back_populates="payments")
    created_by_user = relationship("StaffUser", back_populates="created_payments")
