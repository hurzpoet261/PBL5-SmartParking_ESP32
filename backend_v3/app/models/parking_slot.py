"""
Parking Slot Model
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

from app.utils.timezone import now_local


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
    reserved_customer_id: Optional[str] = None
    reserved_vehicle_id: Optional[str] = None
    reserved_package_id: Optional[str] = None
    reserved_at: Optional[datetime] = None
    slot_type: str = Field("standard", description="standard, vip, disabled")
    created_at: datetime = Field(default_factory=now_local)
    updated_at: datetime = Field(default_factory=now_local)
