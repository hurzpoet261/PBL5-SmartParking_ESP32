"""
Transaction Model (Giao dịch)
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

from app.utils.timezone import now_local


class TransactionType(str, Enum):
    """Transaction types"""
    PARKING_FEE = "parking_fee"
    PACKAGE_PURCHASE = "package_purchase"
    PACKAGE_RENEWAL = "package_renewal"
    REFUND = "refund"
    TOP_UP = "top_up"


class Transaction(BaseModel):
    """Transaction model"""
    transaction_id: str = Field(..., description="Transaction ID (T000001)")
    customer_id: str
    transaction_type: TransactionType
    amount: float = Field(..., description="Amount (VND)")
    session_id: Optional[str] = None
    package_id: Optional[str] = None
    payment_method: str = Field("cash", description="cash, card, wallet")
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=now_local)
