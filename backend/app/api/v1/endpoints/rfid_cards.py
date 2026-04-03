from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundException
from app.models import RFIDCard, StaffUser
from app.schemas.business import RFIDCardCreate, RFIDCardResponse, RFIDCardUpdate
from app.services.business import create_rfid_card, update_model

router = APIRouter()


@router.post("/", response_model=RFIDCardResponse)
def create_rfid_card_api(
    payload: RFIDCardCreate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    return create_rfid_card(db, payload.model_dump())


@router.get("/", response_model=list[RFIDCardResponse])
def list_rfid_cards(
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    stmt = select(RFIDCard).offset(offset).limit(limit)
    return db.execute(stmt).scalars().all()


@router.get("/{card_id}", response_model=RFIDCardResponse)
def get_rfid_card(card_id: int, db: Session = Depends(get_db), _: StaffUser = Depends(get_current_user)):
    card = db.get(RFIDCard, card_id)
    if not card:
        raise NotFoundException("RFID card not found")
    return card


@router.put("/{card_id}", response_model=RFIDCardResponse)
def update_rfid_card_api(
    card_id: int,
    payload: RFIDCardUpdate,
    db: Session = Depends(get_db),
    _: StaffUser = Depends(get_current_user),
):
    card = db.get(RFIDCard, card_id)
    if not card:
        raise NotFoundException("RFID card not found")
    return update_model(db, card, payload.model_dump(exclude_unset=True))
