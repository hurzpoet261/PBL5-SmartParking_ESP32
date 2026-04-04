from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundException
from app.models import ParkingSession, StaffUser
from app.models.enums import SessionStatus
from app.schemas.business import (
    ParkingSessionActionResponse,
    ParkingSessionCheckIn,
    ParkingSessionCheckOut,
    ParkingSessionResponse,
)
from app.services.business import check_in_vehicle, check_out_vehicle

router = APIRouter()


@router.post("/check-in", response_model=ParkingSessionActionResponse)
def check_in_api(
    payload: ParkingSessionCheckIn,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user),
):
    return check_in_vehicle(db, payload.model_dump(), current_user)


@router.post("/check-out", response_model=ParkingSessionActionResponse)
def check_out_api(
    payload: ParkingSessionCheckOut,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user),
):
    return check_out_vehicle(db, payload.model_dump(), current_user)


@router.get("/current", response_model=list[ParkingSessionResponse])
def current_sessions(db: Session = Depends(get_db), _: StaffUser = Depends(get_current_user)):
    stmt = select(ParkingSession).where(ParkingSession.session_status == SessionStatus.IN_PROGRESS)
    return db.execute(stmt).scalars().all()


@router.get("/search-by-plate", response_model=list[ParkingSessionResponse])
def search_by_plate(
    plate_number: str,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    stmt = select(ParkingSession).where(ParkingSession.entry_plate_number.ilike(f"%{plate_number}%"))
    return db.execute(stmt).scalars().all()


@router.get("/", response_model=list[ParkingSessionResponse])
def list_parking_sessions(
    status: SessionStatus | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    stmt = select(ParkingSession)
    if status:
        stmt = stmt.where(ParkingSession.session_status == status)
    stmt = stmt.order_by(ParkingSession.entry_time.desc()).offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()


@router.get("/{session_id}", response_model=ParkingSessionResponse)
def get_parking_session(
    session_id: int,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    session = db.get(ParkingSession, session_id)
    if not session:
        raise NotFoundException("Parking session not found")
    return session
