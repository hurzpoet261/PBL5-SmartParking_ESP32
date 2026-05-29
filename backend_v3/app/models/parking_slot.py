"""
Parking Slot Model
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class SlotStatus(str, Enum):
    """Slot status"""
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"


class ParkingSlot(BaseModel):
    """Parking slot model"""
    slot_id: str = Field(..., description="Slot ID (A01, B05, ...)")
    row: int = Field(..., ge=1, description="Row number")
    col: int = Field(..., ge=1, description="Column number")
    status: SlotStatus = SlotStatus.AVAILABLE
    vehicle_id: Optional[str] = None
    session_id: Optional[str] = None
    slot_type: str = Field("standard", description="standard, vip, disabled")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
