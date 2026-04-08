"""
Customer Model
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum


class CustomerType(str, Enum):
    """Customer types"""
    WALK_IN = "walk_in"          # Khách vãng lai
    DAILY = "daily"               # Gói ngày
    MONTHLY = "monthly"           # Gói tháng
    VIP = "vip"                   # VIP


class Customer(BaseModel):
    """Customer model"""
    customer_id: str = Field(..., description="Customer ID (C000001)")
    name: str = Field(..., min_length=1, max_length=100, description="Full name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    address: Optional[str] = Field(None, max_length=200, description="Address")
    id_card: Optional[str] = Field(None, max_length=20, description="ID Card / CMND")
    customer_type: CustomerType = Field(CustomerType.WALK_IN, description="Customer type")
    balance: float = Field(0.0, description="Account balance (VND)")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(True, description="Active status")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": "C000001",
                "name": "Nguyễn Văn A",
                "phone": "0912345678",
                "email": "nguyenvana@example.com",
                "address": "123 Đường ABC, Quận 1, TP.HCM",
                "id_card": "079012345678",
                "customer_type": "walk_in",
                "balance": 0.0,
                "is_active": True
            }
        }


class CustomerCreate(BaseModel):
    """Schema for creating customer"""
    name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=200)
    id_card: Optional[str] = Field(None, max_length=20)
    customer_type: CustomerType = CustomerType.WALK_IN
    notes: Optional[str] = None


class CustomerUpdate(BaseModel):
    """Schema for updating customer"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=200)
    id_card: Optional[str] = Field(None, max_length=20)
    customer_type: Optional[CustomerType] = None
    balance: Optional[float] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class CustomerResponse(BaseModel):
    """Customer response with additional info"""
    customer: Customer
    total_vehicles: int = 0
    total_sessions: int = 0
    active_sessions: int = 0
    total_spent: float = 0.0
    current_package: Optional[dict] = None
