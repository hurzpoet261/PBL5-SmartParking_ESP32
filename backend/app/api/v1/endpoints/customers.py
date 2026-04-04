from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.exceptions import NotFoundException
from app.models import Customer, StaffUser
from app.schemas.business import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services.business import create_customer, delete_model, update_model

router = APIRouter()


@router.post("/", response_model=CustomerResponse)
def create_customer_api(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    return create_customer(db, payload.model_dump())


@router.get("/", response_model=list[CustomerResponse])
def list_customers(
    search: str | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    stmt = select(Customer)
    if search:
        stmt = stmt.where(or_(Customer.full_name.ilike(f"%{search}%"), Customer.phone.ilike(f"%{search}%")))
    stmt = stmt.offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db), _: StaffUser = Depends(get_current_user)):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise NotFoundException("Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer_api(
    customer_id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise NotFoundException("Customer not found")
    return update_model(db, customer, payload.model_dump(exclude_unset=True))


@router.delete("/{customer_id}")
def delete_customer_api(
    customer_id: int,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(require_admin),
):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise NotFoundException("Customer not found")
    return delete_model(db, customer)
