from sqlalchemy import BigInteger, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import LotStatus


class ParkingLot(BaseModel):
    __tablename__ = "parking_lots"

    lot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    lot_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    lot_name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[LotStatus] = mapped_column(
        Enum(LotStatus, values_callable=lambda x: [e.value for e in x], name="lot_status_enum", create_type=False),
        nullable=False,
        default=LotStatus.ACTIVE,
        server_default=LotStatus.ACTIVE.value,
    )

    zones = relationship("ParkingZone", back_populates="lot")
    gates = relationship("Gate", back_populates="lot")
    staff_users = relationship("StaffUser", back_populates="lot")
    devices = relationship("Device", back_populates="lot")
