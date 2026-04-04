from decimal import Decimal

from sqlalchemy import BigInteger, Enum, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import LotStatus, VehicleType


class MonthlyPlan(BaseModel):
    __tablename__ = "monthly_plans"

    plan_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    plan_name: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_type: Mapped[VehicleType] = mapped_column(
        Enum(VehicleType, values_callable=lambda x: [e.value for e in x], name="vehicle_type_enum", create_type=False),
        nullable=False,
    )
    duration_months: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[LotStatus] = mapped_column(
        Enum(LotStatus, values_callable=lambda x: [e.value for e in x], name="plan_status_enum", create_type=False),
        nullable=False,
        default=LotStatus.ACTIVE,
        server_default=LotStatus.ACTIVE.value,
    )

    subscriptions = relationship("MonthlySubscription", back_populates="plan")
