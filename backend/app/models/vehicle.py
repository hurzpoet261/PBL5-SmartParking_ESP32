from sqlalchemy import BigInteger, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import LotStatus, VehicleType


class Vehicle(BaseModel):
    __tablename__ = "vehicles"
    __table_args__ = (
        Index("ix_vehicles_plate_number", "plate_number"),
    )

    vehicle_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.customer_id"), nullable=True)
    plate_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    vehicle_type: Mapped[VehicleType] = mapped_column(
        Enum(VehicleType, values_callable=lambda x: [e.value for e in x], name="vehicle_type_enum", create_type=False),
        nullable=False,
    )
    brand: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    color: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[LotStatus] = mapped_column(
        Enum(LotStatus, values_callable=lambda x: [e.value for e in x], name="vehicle_status_enum", create_type=False),
        nullable=False,
        default=LotStatus.ACTIVE,
        server_default=LotStatus.ACTIVE.value,
    )

    customer = relationship("Customer", back_populates="vehicles")
    rfid_cards = relationship("RFIDCard", back_populates="assigned_vehicle")
    subscriptions = relationship("MonthlySubscription", back_populates="vehicle")
    parking_sessions = relationship("ParkingSession", back_populates="vehicle")
