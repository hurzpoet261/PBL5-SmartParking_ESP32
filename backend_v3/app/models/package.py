"""
Package Model (Gói cước)
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
from enum import Enum


class PackageType(str, Enum):
    """Package types"""
    PER_USE = "per_use"
    DAILY = "daily"
    MONTHLY = "monthly"


class Package(BaseModel):
    """Package model"""
    package_id: str = Field(..., description="Package ID (P000001)")
    customer_id: str
    vehicle_id: str
    package_type: PackageType
    price: float = Field(..., description="Package price (VND)")
    start_date: datetime = Field(default_factory=datetime.now)
    expire_date: datetime
    remaining_uses: Optional[int] = None
    status: str = Field("active", description="active, expired, cancelled")
    created_at: datetime = Field(default_factory=datetime.now)
    
    @classmethod
    def calculate_expire_date(cls, package_type: PackageType, start_date: datetime = None):
        """Calculate expiration date based on package type"""
        if start_date is None:
            start_date = datetime.now()
        
        if package_type == PackageType.DAILY:
            return start_date + timedelta(days=1)
        elif package_type == PackageType.MONTHLY:
            return start_date + timedelta(days=30)
        else:
            return start_date + timedelta(days=365)


class PackageCreate(BaseModel):
    """Schema for creating package"""
    customer_id: str
    vehicle_id: str
    package_type: PackageType
    remaining_uses: Optional[int] = None
