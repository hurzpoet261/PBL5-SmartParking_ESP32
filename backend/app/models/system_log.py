from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class SystemLog(BaseModel):
    __tablename__ = "system_logs"

    system_log_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("staff_users.user_id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    module_name: Mapped[str] = mapped_column(String(100), nullable=False)
    record_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user = relationship("StaffUser", back_populates="system_logs")
