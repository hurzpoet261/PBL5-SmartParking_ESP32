from datetime import datetime

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import AlertSeverity, AlertStatus, AlertType


class Alert(BaseModel):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_status", "status"),
    )

    alert_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.device_id"), nullable=True)
    alert_type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, values_callable=lambda x: [e.value for e in x], name="alert_type_enum", create_type=False),
        nullable=False,
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, values_callable=lambda x: [e.value for e in x], name="alert_severity_enum", create_type=False),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, values_callable=lambda x: [e.value for e in x], name="alert_status_enum", create_type=False),
        nullable=False,
        default=AlertStatus.OPEN,
        server_default=AlertStatus.OPEN.value,
    )
    detected_at: Mapped[datetime] = mapped_column(nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("staff_users.user_id"), nullable=True)

    device = relationship("Device", back_populates="alerts")
    resolved_by_user = relationship("StaffUser", back_populates="resolved_alerts")
