from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundException
from app.models import Payment, StaffUser
from app.schemas.business import PaymentCreate, PaymentResponse, PaymentUpdate, RevenueItem
from app.services.business import create_payment, get_revenue_daily, get_revenue_monthly, update_model

router = APIRouter()


@router.post("/", response_model=PaymentResponse)
def create_payment_api(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user),
):
    return create_payment(db, payload.model_dump(), current_user.user_id)


@router.get("/", response_model=list[PaymentResponse])
def list_payments(
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    stmt = select(Payment).order_by(Payment.created_at.desc()).offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()


@router.put("/{payment_id}", response_model=PaymentResponse)
def update_payment_api(
    payment_id: int,
    payload: PaymentUpdate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    payment = db.get(Payment, payment_id)
    if not payment:
        raise NotFoundException("Payment not found")
    return update_model(db, payment, payload.model_dump(exclude_unset=True))


@router.get("/revenue/daily", response_model=list[RevenueItem])
def revenue_daily(db: Session = Depends(get_db), _: StaffUser = Depends(get_current_user)):
    return get_revenue_daily(db)


@router.get("/revenue/monthly", response_model=list[RevenueItem])
def revenue_monthly(db: Session = Depends(get_db), _: StaffUser = Depends(get_current_user)):
    return get_revenue_monthly(db)
