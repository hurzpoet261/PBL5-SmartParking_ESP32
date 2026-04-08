"""
RFID Card Model
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class CardStatus(str, Enum):
    """Card status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOST = "lost"
    EXPIRED = "expired"


class RFIDCard(BaseModel):
    """RFID Card model"""
    card_uid: str = Field(..., description="Card UID (0xa3d6ce05)")
    customer_id: str
    vehicle_id: str
    status: CardStatus = CardStatus.ACTIVE
    issued_at: datetime = Field(default_factory=datetime.now)
    expire_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = None


class RFIDCardCreate(BaseModel):
    """Schema for creating RFID card"""
    card_uid: str
    customer_id: str
    vehicle_id: str
    expire_at: Optional[datetime] = None
    notes: Optional[str] = None
