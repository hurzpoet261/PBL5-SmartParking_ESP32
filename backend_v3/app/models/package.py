"""
Package Model (Gói cước)
"""
from pydantic import BaseModel, Field, model_validator
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
    customer_id: str = Field(..., min_length=1)
    vehicle_id: str = Field(..., min_length=1)
    vehicle_type: Optional[str] = None
    package_type: PackageType
    price: float = Field(..., ge=0, description="Package price (VND)")
    start_date: datetime = Field(default_factory=datetime.now)
    expire_date: datetime
    remaining_uses: Optional[int] = Field(None, ge=0)
    consumed_session_ids: list[str] = Field(default_factory=list)
    status: str = Field("active", description="active, expired, cancelled")
    created_at: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="after")
    def validate_remaining_uses(self):
        validate_package_remaining_uses(self.package_type, self.remaining_uses)
        return self
    
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
    customer_id: str = Field(..., min_length=1)
    vehicle_id: str = Field(..., min_length=1)
    package_type: PackageType
    remaining_uses: Optional[int] = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_remaining_uses(self):
        validate_package_remaining_uses(self.package_type, self.remaining_uses)
        return self


def validate_package_remaining_uses(
    package_type: PackageType,
    remaining_uses: Optional[int],
) -> None:
    """Keep prepaid per-use packages finite and unlimited packages unambiguous."""

    if package_type == PackageType.PER_USE:
        if remaining_uses is None or remaining_uses <= 0:
            raise ValueError("per_use package requires remaining_uses > 0")
        return

    if remaining_uses is not None:
        raise ValueError("remaining_uses is only allowed for per_use packages")
