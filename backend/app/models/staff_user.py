from sqlalchemy import BigInteger, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import StaffRole, UserStatus


class StaffUser(BaseModel):
    __tablename__ = "staff_users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    lot_id: Mapped[int | None] = mapped_column(ForeignKey("parking_lots.lot_id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[StaffRole] = mapped_column(
        Enum(StaffRole, values_callable=lambda x: [e.value for e in x], name="staff_role_enum", create_type=False),
        nullable=False,
        default=StaffRole.STAFF,
        server_default=StaffRole.STAFF.value,
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, values_callable=lambda x: [e.value for e in x], name="user_status_enum", create_type=False),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
    )

    lot = relationship("ParkingLot", back_populates="staff_users")
    created_subscriptions = relationship("MonthlySubscription", back_populates="created_by_user")
    entry_sessions = relationship(
        "ParkingSession",
        foreign_keys="ParkingSession.entry_staff_id",
        back_populates="entry_staff",
    )
    exit_sessions = relationship(
        "ParkingSession",
        foreign_keys="ParkingSession.exit_staff_id",
        back_populates="exit_staff",
    )
    created_payments = relationship("Payment", back_populates="created_by_user")
    resolved_alerts = relationship("Alert", back_populates="resolved_by_user")
    system_logs = relationship("SystemLog", back_populates="user")
