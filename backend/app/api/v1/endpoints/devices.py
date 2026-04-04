from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.exceptions import NotFoundException
from app.models import Device, StaffUser
from app.schemas.business import DeviceCreate, DeviceResponse, DeviceStatusUpdate, DeviceUpdate, GasAlertCreate
from app.services.business import create_device, delete_model, process_gas_alert, update_model

router = APIRouter()


@router.post("/", response_model=DeviceResponse)
def create_device_api(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    return create_device(db, payload.model_dump())


@router.get("/", response_model=list[DeviceResponse])
def list_devices(
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    stmt = select(Device).offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(device_id: int, db: Session = Depends(get_db), _: StaffUser = Depends(get_current_user)):
    device = db.get(Device, device_id)
    if not device:
        raise NotFoundException("Device not found")
    return device


@router.put("/{device_id}", response_model=DeviceResponse)
def update_device_api(
    device_id: int,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    device = db.get(Device, device_id)
    if not device:
        raise NotFoundException("Device not found")
    return update_model(db, device, payload.model_dump(exclude_unset=True))


@router.delete("/{device_id}")
def delete_device_api(
    device_id: int,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(require_admin),
):
    device = db.get(Device, device_id)
    if not device:
        raise NotFoundException("Device not found")
    return delete_model(db, device)


@router.put("/{device_id}/status", response_model=DeviceResponse)
def update_device_status_api(
    device_id: int,
    payload: DeviceStatusUpdate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    device = db.get(Device, device_id)
    if not device:
        raise NotFoundException("Device not found")
    return update_model(db, device, payload.model_dump(exclude_unset=True))


@router.post("/gas-alert")
def gas_alert_api(
    payload: GasAlertCreate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    return process_gas_alert(db, payload.device_id, payload.gas_value)
