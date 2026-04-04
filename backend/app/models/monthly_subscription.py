from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, Enum, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import SubscriptionStatus


class MonthlySubscription(BaseModel):
    __tablename__ = "monthly_subscriptions"
    __table_args__ = (
        Index("ix_monthly_subscriptions_end_date", "end_date"),
    )

    subscription_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("monthly_plans.plan_id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"), nullable=False)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.vehicle_id"), nullable=False)
    card_id: Mapped[int | None] = mapped_column(ForeignKey("rfid_cards.card_id"), nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    registered_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, values_callable=lambda x: [e.value for e in x], name="subscription_status_enum", create_type=False),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
        server_default=SubscriptionStatus.ACTIVE.value,
    )
    created_by: Mapped[int | None] = mapped_column(ForeignKey("staff_users.user_id"), nullable=True)

    plan = relationship("MonthlyPlan", back_populates="subscriptions")
    customer = relationship("Customer", back_populates="subscriptions")
    vehicle = relationship("Vehicle", back_populates="subscriptions")
    card = relationship("RFIDCard", back_populates="subscriptions")
    created_by_user = relationship("StaffUser", back_populates="created_subscriptions")
    parking_sessions = relationship("ParkingSession", back_populates="subscription")
    payments = relationship("Payment", back_populates="subscription")
