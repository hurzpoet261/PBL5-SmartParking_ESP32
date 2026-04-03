from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.exceptions import NotFoundException
from app.models import MonthlySubscription, StaffUser
from app.models.enums import SubscriptionStatus
from app.schemas.business import (
    MonthlySubscriptionCreate,
    MonthlySubscriptionResponse,
    MonthlySubscriptionUpdate,
)
from app.services.business import create_monthly_subscription, delete_model, update_model

router = APIRouter()


@router.get("/expiring-soon", response_model=list[MonthlySubscriptionResponse])
def expiring_soon(
    days: int = 7,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    today = date.today()
    target_day = today + timedelta(days=days)
    stmt = select(MonthlySubscription).where(
        MonthlySubscription.status == SubscriptionStatus.ACTIVE,
        MonthlySubscription.end_date >= today,
        MonthlySubscription.end_date <= target_day,
    )
    return db.execute(stmt).scalars().all()


@router.post("/", response_model=MonthlySubscriptionResponse)
def create_monthly_subscription_api(
    payload: MonthlySubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user),
):
    return create_monthly_subscription(db, payload.model_dump(), current_user.user_id)


@router.get("/", response_model=list[MonthlySubscriptionResponse])
def list_monthly_subscriptions(
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    stmt = select(MonthlySubscription).offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()


@router.get("/{subscription_id}", response_model=MonthlySubscriptionResponse)
def get_monthly_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    subscription = db.get(MonthlySubscription, subscription_id)
    if not subscription:
        raise NotFoundException("Monthly subscription not found")
    return subscription


@router.put("/{subscription_id}", response_model=MonthlySubscriptionResponse)
def update_monthly_subscription_api(
    subscription_id: int,
    payload: MonthlySubscriptionUpdate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    subscription = db.get(MonthlySubscription, subscription_id)
    if not subscription:
        raise NotFoundException("Monthly subscription not found")
    return update_model(db, subscription, payload.model_dump(exclude_unset=True))


@router.delete("/{subscription_id}")
def delete_monthly_subscription_api(
    subscription_id: int,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(require_admin),
):
    subscription = db.get(MonthlySubscription, subscription_id)
    if not subscription:
        raise NotFoundException("Monthly subscription not found")
    return delete_model(db, subscription)
