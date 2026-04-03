from sqlalchemy import BigInteger, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import CustomerType, UserStatus


class Customer(BaseModel):
    __tablename__ = "customers"

    customer_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    customer_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_type: Mapped[CustomerType] = mapped_column(
        Enum(CustomerType, values_callable=lambda x: [e.value for e in x], name="customer_type_enum", create_type=False),
        nullable=False,
        default=CustomerType.WALK_IN,
        server_default=CustomerType.WALK_IN.value,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, values_callable=lambda x: [e.value for e in x], name="customer_status_enum", create_type=False),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
    )

    vehicles = relationship("Vehicle", back_populates="customer")
    subscriptions = relationship("MonthlySubscription", back_populates="customer")
    parking_sessions = relationship("ParkingSession", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")
    rfid_cards = relationship("RFIDCard", back_populates="assigned_customer")
