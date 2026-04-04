from datetime import datetime

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import DeviceStatus, DeviceType


class Device(BaseModel):
    __tablename__ = "devices"
    __table_args__ = (
        Index("ix_devices_status", "status"),
    )

    device_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    lot_id: Mapped[int | None] = mapped_column(ForeignKey("parking_lots.lot_id"), nullable=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("parking_zones.zone_id"), nullable=True)
    gate_id: Mapped[int | None] = mapped_column(ForeignKey("gates.gate_id"), nullable=True)
    device_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    device_name: Mapped[str] = mapped_column(String(100), nullable=False)
    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType, values_callable=lambda x: [e.value for e in x], name="device_type_enum", create_type=False),
        nullable=False,
    )
    serial_number: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus, values_callable=lambda x: [e.value for e in x], name="device_status_enum", create_type=False),
        nullable=False,
        default=DeviceStatus.ONLINE,
        server_default=DeviceStatus.ONLINE.value,
    )
    installed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    lot = relationship("ParkingLot", back_populates="devices")
    zone = relationship("ParkingZone", back_populates="devices")
    gate = relationship("Gate", back_populates="devices")
    alerts = relationship("Alert", back_populates="device")
    device_logs = relationship("DeviceLog", back_populates="device")
