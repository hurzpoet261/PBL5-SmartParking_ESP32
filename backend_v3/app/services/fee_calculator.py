"""
Fee Calculator Service
"""
import math
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.config import settings
from app.models.package import PackageType


class FeeBreakdown(BaseModel):
    """Auditable parking fee calculation stored with session and transaction."""

    base_fee: float = Field(..., ge=0)
    discount: float = Field(..., ge=0)
    package_applied: bool
    package_id: Optional[str] = None
    package_type: Optional[str] = None
    final_fee: float = Field(..., ge=0)
    reason: str
    remaining_uses_after: Optional[int] = Field(None, ge=0)


class FeeCalculator:
    """Calculate parking fees"""
    
    @staticmethod
    def calculate_base_fee(entry_time: datetime, exit_time: datetime) -> float:
        """Calculate the normal hourly fee before applying a package."""

        # Calculate duration in hours
        duration = (exit_time - entry_time).total_seconds() / 3600
        
        # Round up to nearest hour
        hours = math.ceil(duration)
        
        # Minimum 1 hour
        hours = max(1, hours)
        
        # Calculate fee
        fee = hours * settings.FEE_PER_HOUR
        
        return float(fee)

    @staticmethod
    def calculate_parking_fee(
        entry_time: datetime,
        exit_time: datetime,
        package_type: str = None,
    ) -> float:
        """Compatibility wrapper that never applies an unvalidated package."""

        del package_type
        return FeeCalculator.calculate_base_fee(entry_time, exit_time)

    @staticmethod
    def build_fee_breakdown(
        entry_time: datetime,
        exit_time: datetime,
        package: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a persisted audit record for package application."""

        base_fee = FeeCalculator.calculate_base_fee(entry_time, exit_time)
        if not package:
            return FeeBreakdown(
                base_fee=base_fee,
                discount=0.0,
                package_applied=False,
                final_fee=base_fee,
                reason="No eligible package for this vehicle at checkout.",
            ).model_dump()

        package_type = str(package["package_type"])
        return FeeBreakdown(
            base_fee=base_fee,
            discount=base_fee,
            package_applied=True,
            package_id=package["package_id"],
            package_type=package_type,
            final_fee=0.0,
            reason=f"Applied active {package_type} package for the registered vehicle.",
            remaining_uses_after=package.get("remaining_uses"),
        ).model_dump()
    
    @staticmethod
    def get_package_price(
        package_type: PackageType,
        remaining_uses: Optional[int] = None,
    ) -> float:
        """Get package price"""
        if package_type == PackageType.PER_USE:
            if remaining_uses is None or remaining_uses <= 0:
                raise ValueError("per_use package requires remaining_uses > 0")
            return float(settings.FEE_PER_HOUR * remaining_uses)
        if package_type == PackageType.DAILY:
            return float(settings.FEE_DAILY_PACKAGE)
        elif package_type == PackageType.MONTHLY:
            return float(settings.FEE_MONTHLY_PACKAGE)
        raise ValueError(f"Unsupported package type: {package_type}")
