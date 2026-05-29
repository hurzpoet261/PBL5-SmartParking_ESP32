"""
Vehicle Model
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class VehicleType(str, Enum):
    """Vehicle types"""
    MOTORBIKE = "motorbike"
    CAR = "car"
    BICYCLE = "bicycle"
    TRUCK = "truck"


class Vehicle(BaseModel):
    """Vehicle model"""
    vehicle_id: str = Field(..., description="Vehicle ID (V000001)")
    customer_id: str = Field(..., description="Owner customer ID")
    plate_number: str = Field(..., description="License plate number")
    vehicle_type: VehicleType = Field(VehicleType.MOTORBIKE)
    brand: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=30)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(True)
    
    class Config:
        json_schema_extra = {
            "example": {
                "vehicle_id": "V000001",
                "customer_id": "C000001",
                "plate_number": "59A1-12345",
                "vehicle_type": "motorbike",
                "brand": "Honda",
                "model": "Wave Alpha",
                "color": "Đỏ"
            }
        }


class VehicleCreate(BaseModel):
    """Schema for creating vehicle"""
    customer_id: str
    plate_number: str = Field(..., min_length=1)
    vehicle_type: VehicleType = VehicleType.MOTORBIKE
    brand: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None


class VehicleUpdate(BaseModel):
    """Schema for updating vehicle"""
    plate_number: Optional[str] = None
    vehicle_type: Optional[VehicleType] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None
