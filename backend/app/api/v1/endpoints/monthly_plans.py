from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.exceptions import NotFoundException
from app.models import MonthlyPlan, StaffUser
from app.schemas.business import MonthlyPlanCreate, MonthlyPlanResponse, MonthlyPlanUpdate
from app.services.business import create_monthly_plan, delete_model, update_model

router = APIRouter()


@router.post("/", response_model=MonthlyPlanResponse)
def create_monthly_plan_api(
    payload: MonthlyPlanCreate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    return create_monthly_plan(db, payload.model_dump())


@router.get("/", response_model=list[MonthlyPlanResponse])
def list_monthly_plans(
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    stmt = select(MonthlyPlan).offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()


@router.get("/{plan_id}", response_model=MonthlyPlanResponse)
def get_monthly_plan(plan_id: int, db: Session = Depends(get_db), _: StaffUser = Depends(get_current_user)):
    plan = db.get(MonthlyPlan, plan_id)
    if not plan:
        raise NotFoundException("Monthly plan not found")
    return plan


@router.put("/{plan_id}", response_model=MonthlyPlanResponse)
def update_monthly_plan_api(
    plan_id: int,
    payload: MonthlyPlanUpdate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    plan = db.get(MonthlyPlan, plan_id)
    if not plan:
        raise NotFoundException("Monthly plan not found")
    return update_model(db, plan, payload.model_dump(exclude_unset=True))


@router.delete("/{plan_id}")
def delete_monthly_plan_api(
    plan_id: int,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(require_admin),
):
    plan = db.get(MonthlyPlan, plan_id)
    if not plan:
        raise NotFoundException("Monthly plan not found")
    return delete_model(db, plan)
