from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.exceptions import NotFoundException
from app.models import StaffUser, Vehicle
from app.schemas.business import VehicleCreate, VehicleResponse, VehicleUpdate
from app.services.business import create_vehicle, delete_model, update_model

router = APIRouter()


@router.post("/", response_model=VehicleResponse)
def create_vehicle_api(
    payload: VehicleCreate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    return create_vehicle(db, payload.model_dump())


@router.get("/", response_model=list[VehicleResponse])
def list_vehicles(
    search: str | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    stmt = select(Vehicle)
    if search:
        stmt = stmt.where(Vehicle.plate_number.ilike(f"%{search}%"))
    stmt = stmt.offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db), _: StaffUser = Depends(get_current_user)):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise NotFoundException("Vehicle not found")
    return vehicle


@router.put("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle_api(
    vehicle_id: int,
    payload: VehicleUpdate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise NotFoundException("Vehicle not found")
    return update_model(db, vehicle, payload.model_dump(exclude_unset=True))


@router.delete("/{vehicle_id}")
def delete_vehicle_api(
    vehicle_id: int,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(require_admin),
):
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise NotFoundException("Vehicle not found")
    return delete_model(db, vehicle)
