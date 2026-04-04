from datetime import datetime

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import CardStatus, CardType


class RFIDCard(BaseModel):
    __tablename__ = "rfid_cards"
    __table_args__ = (
        Index("ix_rfid_cards_card_uid", "card_uid"),
    )

    card_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    card_uid: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    card_code: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    card_type: Mapped[CardType] = mapped_column(
        Enum(CardType, values_callable=lambda x: [e.value for e in x], name="card_type_enum", create_type=False),
        nullable=False,
    )
    assigned_customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.customer_id"), nullable=True)
    assigned_vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.vehicle_id"), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[CardStatus] = mapped_column(
        Enum(CardStatus, values_callable=lambda x: [e.value for e in x], name="card_status_enum", create_type=False),
        nullable=False,
        default=CardStatus.AVAILABLE,
        server_default=CardStatus.AVAILABLE.value,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    assigned_customer = relationship("Customer", back_populates="rfid_cards")
    assigned_vehicle = relationship("Vehicle", back_populates="rfid_cards")
    subscriptions = relationship("MonthlySubscription", back_populates="card")
    parking_sessions = relationship("ParkingSession", back_populates="card")
