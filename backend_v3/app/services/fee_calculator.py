"""
Fee Calculator Service
"""
from datetime import datetime
from app.config import settings
from app.models.package import PackageType
import math


class FeeCalculator:
    """Calculate parking fees"""
    
    @staticmethod
    def calculate_parking_fee(entry_time: datetime, exit_time: datetime, package_type: str = None) -> float:
        """
        Calculate parking fee based on duration
        
        Args:
            entry_time: Entry timestamp
            exit_time: Exit timestamp
            package_type: Package type (if any)
        
        Returns:
            Parking fee in VND
        """
        # If has package, no fee
        if package_type in [PackageType.DAILY.value, PackageType.MONTHLY.value]:
            return 0.0
        
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
    def get_package_price(package_type: PackageType) -> float:
        """Get package price"""
        if package_type == PackageType.DAILY:
            return float(settings.FEE_DAILY_PACKAGE)
        elif package_type == PackageType.MONTHLY:
            return float(settings.FEE_MONTHLY_PACKAGE)
        else:  # PER_USE
            return 0.0  # Pay per use
