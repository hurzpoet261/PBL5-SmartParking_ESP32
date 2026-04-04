from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import GateStatus, GateType


class Gate(BaseModel):
    __tablename__ = "gates"

    gate_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("parking_lots.lot_id"), nullable=False)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("parking_zones.zone_id"), nullable=True)
    gate_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    gate_name: Mapped[str] = mapped_column(String(100), nullable=False)
    gate_type: Mapped[GateType] = mapped_column(
        Enum(GateType, values_callable=lambda x: [e.value for e in x], name="gate_type_enum", create_type=False),
        nullable=False,
    )
    status: Mapped[GateStatus] = mapped_column(
        Enum(GateStatus, values_callable=lambda x: [e.value for e in x], name="gate_status_enum", create_type=False),
        nullable=False,
        default=GateStatus.ACTIVE,
        server_default=GateStatus.ACTIVE.value,
    )

    lot = relationship("ParkingLot", back_populates="gates")
    zone = relationship("ParkingZone", back_populates="gates")
    entry_sessions = relationship(
        "ParkingSession",
        foreign_keys="ParkingSession.entry_gate_id",
        back_populates="entry_gate",
    )
    exit_sessions = relationship(
        "ParkingSession",
        foreign_keys="ParkingSession.exit_gate_id",
        back_populates="exit_gate",
    )
    devices = relationship("Device", back_populates="gate")
