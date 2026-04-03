from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import LotStatus, VehicleType


class ParkingZone(BaseModel):
    __tablename__ = "parking_zones"

    zone_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("parking_lots.lot_id"), nullable=False)
    zone_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    zone_name: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_type: Mapped[VehicleType] = mapped_column(
        Enum(VehicleType, values_callable=lambda x: [e.value for e in x], name="vehicle_type_enum"),
        nullable=False,
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[LotStatus] = mapped_column(
        Enum(LotStatus, values_callable=lambda x: [e.value for e in x], name="zone_status_enum", create_type=False),
        nullable=False,
        default=LotStatus.ACTIVE,
        server_default=LotStatus.ACTIVE.value,
    )

    lot = relationship("ParkingLot", back_populates="zones")
    gates = relationship("Gate", back_populates="zone")
    devices = relationship("Device", back_populates="zone")
