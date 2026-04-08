"""
Parking Session Model
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class SessionStatus(str, Enum):
    """Session status"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Session(BaseModel):
    """Parking session model"""
    session_id: str = Field(..., description="Session ID (S000001)")
    card_uid: str
    customer_id: str
    vehicle_id: str
    slot_id: Optional[str] = None
    entry_gate_id: int = 1
    exit_gate_id: Optional[int] = None
    entry_time: datetime = Field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    distance_cm: Optional[float] = None
    status: SessionStatus = SessionStatus.IN_PROGRESS
    parking_fee: float = 0.0
    package_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class SessionCreate(BaseModel):
    """Schema for creating session"""
    card_uid: str
    customer_id: str
    vehicle_id: str
    slot_id: Optional[str] = None
    entry_gate_id: int = 1
    distance_cm: Optional[float] = None
