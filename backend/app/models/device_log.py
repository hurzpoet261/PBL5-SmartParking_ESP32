from decimal import Decimal

from sqlalchemy import BigInteger, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import LogLevel


class DeviceLog(BaseModel):
    __tablename__ = "device_logs"

    log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.device_id"), nullable=False)
    log_type: Mapped[str] = mapped_column(String(50), nullable=False)
    log_level: Mapped[LogLevel] = mapped_column(
        Enum(LogLevel, values_callable=lambda x: [e.value for e in x], name="log_level_enum", create_type=False),
        nullable=False,
        default=LogLevel.INFO,
        server_default=LogLevel.INFO.value,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sensor_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    device = relationship("Device", back_populates="device_logs")
