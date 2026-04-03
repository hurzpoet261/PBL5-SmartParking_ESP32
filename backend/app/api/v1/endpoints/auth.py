from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import StaffUser
from app.schemas.auth import LoginRequest, StaffUserResponse
from app.schemas.common import TokenResponse
from app.services.business import login_user

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    token, _ = login_user(db, payload.username, payload.password)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=StaffUserResponse)
def get_me(current_user: StaffUser = Depends(get_current_user)):
    return current_user
